"""
Field-matching logic — the verification core.

This module is deliberately free of any web/OCR dependency: it takes the text
already extracted from a label plus the expected application values, and decides
whether each field matches. Keeping it pure makes it fast, fully unit-testable
without images, and easy to explain in a review.

Every field gets a *different* rule, because matching a brand name is not the
same problem as matching a legally-fixed warning statement or a percentage.
"""

import re
from rapidfuzz import fuzz

# Status values used throughout the app / UI.
PASS = "pass"            # confident match
REVIEW = "review"        # probably matches, but a human should glance at it
MISMATCH = "mismatch"    # found the field, value disagrees
NOT_FOUND = "not_found"  # couldn't locate it on the label at all

FIELD_LABELS = {
    "brand_name": "Brand name",
    "class_type": "Class/type designation",
    "alcohol_content": "Alcohol content (ABV)",
    "net_contents": "Net contents",
    "producer_name_address": "Producer name & address",
    "country_of_origin": "Country of origin",
    "government_warning": "Government health warning",
}


def _result(field, status, expected, found, confidence, message):
    return {
        "field": field,
        "label": FIELD_LABELS.get(field, field),
        "status": status,
        "expected": expected,
        "found": found,
        "confidence": round(float(confidence), 1),
        "message": message,
    }


def _best_line(needle, lines):
    """Return the label line most similar to `needle`, with its score (0-100)."""
    if not lines:
        return "", 0.0
    # Case-insensitive scoring: rapidfuzz is case-sensitive by default, which
    # would rank a correctly-cased label line LOW (and break case-difference
    # detection for brand names). We compare case-folded, but return the line's
    # ORIGINAL text so the caller can still inspect its real casing.
    nl = needle.lower()
    scored = [(ln, fuzz.token_set_ratio(nl, ln.lower())) for ln in lines]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0]


def _alnum(s):
    """Collapse to lowercase alphanumerics — strips case & punctuation for comparison."""
    return re.sub(r"[^a-z0-9]", "", s.lower())


# ---------------------------------------------------------------------------
# Per-field matchers
# ---------------------------------------------------------------------------

def match_brand(expected, full_text, lines):
    """
    Brand name. We preserve nuance on purpose (Dave's "STONE'S THROW" vs
    "Stone's Throw"): if the letters match but case/punctuation differs, that is
    NOT an automatic pass — it's flagged for human review.
    """
    found_line, score = _best_line(expected, lines)
    if _alnum(expected) and _alnum(expected) == _alnum(found_line):
        if expected.strip() == found_line.strip():
            return _result("brand_name", PASS, expected, found_line, 100,
                           "Exact match.")
        return _result("brand_name", REVIEW, expected, found_line, score,
                       f'Text matches but formatting differs — label shows "{found_line}". '
                       "Confirm case/punctuation is acceptable.")
    return _match_fuzzy_core("brand_name", expected, full_text, found_line, score)


def match_generic_fuzzy(field, expected, full_text, lines):
    """Producer, country of origin — fuzzy text presence check."""
    found_line, line_score = _best_line(expected, lines)
    return _match_fuzzy_core(field, expected, full_text, found_line, line_score)


# COLA "class/type" is a CATEGORY CODE ("TABLE RED WINE"), but the label prints a
# specific designation ("Cabernet Sauvignon"). This maps each family to the
# on-label terms that satisfy it. Deliberately compact: ~15 families cover
# essentially all consumer labels; the official TTB code list is far longer but
# collapses into these, and any unmapped class falls back to fuzzy matching.
CLASS_FAMILIES = {
    "red wine": ["red wine", "red table wine", "rouge", "red blend", "cabernet",
                 "cabernet sauvignon", "cabernet franc", "merlot", "pinot noir",
                 "syrah", "shiraz", "zinfandel", "malbec", "sangiovese", "tempranillo",
                 "grenache", "petite sirah", "petit verdot", "barbera", "nebbiolo",
                 "carmenere", "claret", "bordeaux", "chianti", "rioja", "montepulciano"],
    "white wine": ["white wine", "white table wine", "blanc", "white blend",
                   "chardonnay", "sauvignon blanc", "pinot grigio", "pinot gris",
                   "riesling", "moscato", "muscat", "viognier", "chenin blanc",
                   "gewurztraminer", "albarino", "verdejo", "gruner veltliner",
                   "semillon", "trebbiano", "vermentino"],
    "rose wine": ["rose", "rose wine", "blush", "white zinfandel", "rosado"],
    "sparkling wine": ["sparkling", "sparkling wine", "champagne", "cremant", "cava",
                       "prosecco", "brut", "spumante", "blanc de blancs", "blanc de noirs"],
    "dessert wine": ["dessert wine", "port", "tawny", "sherry", "madeira", "marsala",
                     "muscatel", "fortified", "tokaji", "ice wine", "late harvest", "sauternes"],
    "flavored wine": ["flavored wine", "sangria", "fruit wine", "apple wine", "berry wine"],
    "whisky": ["whisky", "whiskey", "bourbon", "rye", "scotch", "single malt", "moonshine"],
    "vodka": ["vodka"],
    "gin": ["gin"],
    "rum": ["rum", "rhum", "cachaca"],
    "tequila": ["tequila", "mezcal", "agave"],
    "brandy": ["brandy", "cognac", "armagnac", "eau de vie", "grappa", "pisco"],
    "liqueur": ["liqueur", "cordial", "schnapps", "aperitif", "amaro", "bitters"],
    "beer": ["beer", "ale", "lager", "ipa", "stout", "porter", "pilsner", "malt beverage", "hard seltzer"],
    "cider": ["cider", "cidre", "perry"],
}


def _normalize_class(s):
    """Strip TTB code cruft: 'TABLE', parentheticals, slashes -> a clean phrase."""
    s = s.lower()
    s = re.sub(r"\([^)]*\)", " ", s)      # drop "(cooking)" etc.
    s = s.replace("/", " ").replace("table", " ")
    return re.sub(r"\s+", " ", s).strip()


def match_class(expected, full_text, lines):
    """
    Class/type. Resolve the application's class CODE to its family, then pass if
    the label shows the family name OR any member designation (a varietal, etc.).
    Falls back to plain fuzzy matching for classes not in the family map.
    """
    exp_norm = _normalize_class(expected)
    label = full_text.lower()

    # Which families does the expected code belong to? (e.g. "dessert /port/sherry"
    # hits the dessert family via several of its terms.)
    acceptable, family = set(), None
    for fam, terms in CLASS_FAMILIES.items():
        if fam in exp_norm or any(t in exp_norm for t in terms):
            acceptable.update([fam] + terms)
            family = family or fam

    if not acceptable:
        # Unmapped class — behave exactly as before.
        return match_generic_fuzzy("class_type", expected, full_text, lines)

    # Pass if any acceptable designation appears on the label. We check two ways:
    #  1. whole-word match (handles short terms like "gin" without false hits);
    #  2. substring against a de-spaced label for longer terms — OCR routinely
    #     drops spaces ("CABERNETSAUVIGNON"), which a \b match would miss.
    label_compact = re.sub(r"[^a-z0-9]", "", label)
    for term in sorted(acceptable, key=len, reverse=True):
        term_compact = re.sub(r"[^a-z0-9]", "", term)
        if re.search(r"\b" + re.escape(term) + r"\b", label) or \
           (len(term_compact) >= 5 and term_compact in label_compact):
            return _result("class_type", PASS, expected, term, 100,
                           f'Label shows "{term}", which satisfies "{expected}".')

    examples = ", ".join(CLASS_FAMILIES[family][:4])
    return _result("class_type", NOT_FOUND, expected, None, 0,
                   f'Expected a {family} designation (e.g. {examples}); none found on label.')


def _match_fuzzy_core(field, expected, full_text, found_line, line_score):
    # partial_ratio finds the best-matching substring anywhere in the label text,
    # so it survives surrounding OCR noise.
    score = max(line_score, fuzz.partial_ratio(expected.lower(), full_text.lower()))
    if score >= 88:
        return _result(field, PASS, expected, found_line, score, "Match found on label.")
    if score >= 72:
        return _result(field, REVIEW, expected, found_line, score,
                       "Close match — recommend human review (possible OCR noise).")
    return _result(field, NOT_FOUND, expected, found_line or None, score,
                   "Could not confidently find this on the label.")


def match_abv(expected, full_text, lines):
    """
    Alcohol content. Compare the NUMBER, not the string — "13.5%" and
    "13.5% ALC/VOL" both satisfy an expected "13.5".

    This is label-vs-application, so the printed value must match what the
    application declared (we do NOT apply the 27 CFR 4.36 production tolerance,
    which governs *actual* vs *labeled* alcohol — a different axis). We only
    allow tiny slack (OCR noise). But 4.36 does permit two label forms the naive
    matcher would wrongly fail, which we handle:
      1. A stated RANGE, e.g. "12% to 14%" — pass if the declared value is inside.
      2. "TABLE WINE" / "LIGHT WINE" — a legal alternative to a numeric statement
         for wines <=14% ABV. Flagged REVIEW so the agent confirms the wine
         qualifies.
    """
    OCR_SLACK = 0.05
    want = _parse_number(expected)
    if want is None:
        return _result("alcohol_content", REVIEW, expected, None, 0,
                       "Expected ABV value could not be parsed.")

    # (1) Range statement on the label, e.g. "12% to 14%" / "12-14% ALC BY VOL".
    rng = _find_abv_range(full_text)
    if rng and rng[0] - OCR_SLACK <= want <= rng[1] + OCR_SLACK:
        return _result("alcohol_content", PASS, expected, f"{rng[0]}%–{rng[1]}%", 100,
                       f"Declared {expected} falls within the label's stated range.")

    # (2) Exact numeric match (the normal case).
    found_numbers = _find_percentages(full_text)
    for num, raw in found_numbers:
        if abs(num - want) <= OCR_SLACK:
            return _result("alcohol_content", PASS, expected, raw, 100,
                           f"ABV matches ({raw}).")

    # (3) "Table wine" / "light wine" — allowed without a number for <=14% ABV.
    low = full_text.lower()
    if ("table wine" in low or "light wine" in low) and want <= 14.0:
        return _result("alcohol_content", REVIEW, expected, "table/light wine", 70,
                       'Label uses "table/light wine" instead of a number — '
                       "permitted for wines ≤14% ABV. Confirm the wine qualifies.")

    if found_numbers:
        nearest = min(found_numbers, key=lambda x: abs(x[0] - want))
        return _result("alcohol_content", MISMATCH, expected, nearest[1], 60,
                       f"Label shows {nearest[1]}, application says {expected}.")
    return _result("alcohol_content", NOT_FOUND, expected, None, 0,
                   "No alcohol percentage found on the label.")


def _find_abv_range(text):
    """Detect a stated ABV range like '12% to 14%' or '12-14%'. Returns (lo, hi)."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*%?\s*(?:to|-|–|—)\s*(\d+(?:\.\d+)?)\s*%", text, re.I)
    if not m:
        return None
    lo, hi = float(m.group(1)), float(m.group(2))
    return (min(lo, hi), max(lo, hi))


def match_net_contents(expected, full_text, lines):
    """Net contents — compare quantity + unit, tolerant of spacing (750mL == 750 mL)."""
    want = _parse_quantity(expected)
    if want is None:
        return _match_fuzzy_core("net_contents", expected, full_text,
                                 *(_best_line(expected, lines))[::-1])
    for val, unit, raw in _find_quantities(full_text):
        if abs(val - want[0]) < 0.001 and unit == want[1]:
            return _result("net_contents", PASS, expected, raw, 100,
                           f"Net contents match ({raw}).")
    found = _find_quantities(full_text)
    if found:
        return _result("net_contents", MISMATCH, expected, found[0][2], 60,
                       f"Label shows {found[0][2]}, application says {expected}.")
    return _result("net_contents", NOT_FOUND, expected, None, 0,
                   "No net-contents value found on the label.")


def match_government_warning(expected, full_text, lines):
    """
    The strictest field (Jenny). Requirements: exact text, ALL CAPS, bold.
    - Text/exactness: fuzzy-match the full statement so a single OCR slip doesn't
      fail an otherwise-correct label, but require a very high score.
    - ALL CAPS: verified directly.
    - BOLD: cannot be determined from OCR text — we flag it for human eyes rather
      than pretend to check it. (Saying what we *can't* verify is the honest call.)
    """
    norm_text = re.sub(r"\s+", " ", full_text).strip()
    norm_want = re.sub(r"\s+", " ", expected).strip()

    score = fuzz.partial_ratio(norm_want.lower(), norm_text.lower())
    has_header = "GOVERNMENT WARNING" in full_text  # exact-case check

    if score >= 96 and has_header:
        return _result("government_warning", REVIEW, expected,
                       "GOVERNMENT WARNING: …", score,
                       "Warning text present and in ALL CAPS. "
                       "Bold styling cannot be verified by OCR — please confirm visually.")
    if score >= 96 and not has_header:
        return _result("government_warning", MISMATCH, expected,
                       "warning text present (not all caps)", score,
                       "Warning text is present but NOT in required ALL CAPS.")
    if score >= 80:
        return _result("government_warning", MISMATCH, expected, None, score,
                       "Warning text is present but does not exactly match the required statement.")

    # Partial detection: on hard labels (small, low-contrast print) OCR often
    # garbles the warning enough to miss the exact-match threshold, yet clearly
    # reads several of its distinctive phrases. Rather than a flat "not found"
    # (which reads as "the warning is absent"), flag it for a human to confirm —
    # the warning is likely there, just unreadable to OCR. Fail-safe, informative.
    fragments = _count_warning_fragments(norm_text)
    if fragments >= 2:
        return _result("government_warning", REVIEW, expected,
                       f"{fragments} warning phrases detected", score,
                       "Warning text partially detected but too unclear to verify exactly "
                       "(small/low-contrast print). Please confirm manually.")

    return _result("government_warning", NOT_FOUND, expected, None, score,
                   "Required government warning statement not found.")


# Distinctive phrases from the federal warning. Used only to decide whether a
# garbled OCR read still contains *enough* of the warning to warrant human review.
_WARNING_FRAGMENTS = (
    "surgeon general",
    "birth defects",
    "operate machinery",
    "health problems",
    "during pregnancy",
    "government warning",
)


def _count_warning_fragments(norm_text):
    low = norm_text.lower()
    return sum(1 for frag in _WARNING_FRAGMENTS
               if fuzz.partial_ratio(frag, low) >= 85)


# ---------------------------------------------------------------------------
# Small parsing helpers
# ---------------------------------------------------------------------------

def _parse_number(s):
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    return float(m.group(1)) if m else None


def _find_percentages(text):
    """All 'NN.N%' occurrences -> list of (value, raw_string)."""
    out = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*%", text):
        out.append((float(m.group(1)), m.group(0).strip()))
    return out


_UNIT_NORM = {
    "ml": "ml", "milliliter": "ml", "milliliters": "ml",
    "l": "l", "liter": "l", "litre": "l", "liters": "l", "litres": "l",
    "oz": "oz", "floz": "oz", "fl oz": "oz", "fluidounce": "oz",
}


def _norm_unit(u):
    return _UNIT_NORM.get(re.sub(r"[^a-z]", "", u.lower()), u.lower())


def _parse_quantity(s):
    m = re.search(r"(\d+(?:\.\d+)?)\s*(ml|l|fl\.?\s*oz|oz|liters?|litres?|milliliters?)", s, re.I)
    if not m:
        return None
    return float(m.group(1)), _norm_unit(m.group(2))


def _find_quantities(text):
    out = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*(ml|l|fl\.?\s*oz|oz|liters?|litres?|milliliters?)", text, re.I):
        out.append((float(m.group(1)), _norm_unit(m.group(2)), m.group(0).strip()))
    return out


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

# Maps each expected field to the matcher that handles it.
_DISPATCH = {
    "brand_name": match_brand,
    "class_type": match_class,
    "alcohol_content": match_abv,
    "net_contents": match_net_contents,
    "government_warning": match_government_warning,
    # everything else uses the generic fuzzy matcher
}


def verify_fields(full_text, expected):
    """
    `expected` is a dict of {field: value}. Only fields the agent actually filled
    in are checked. Returns a list of result dicts plus an overall summary.
    """
    lines = [ln.strip() for ln in full_text.splitlines() if ln.strip()]
    results = []
    for field, value in expected.items():
        if not value or not value.strip():
            continue
        matcher = _DISPATCH.get(field)
        if matcher:
            results.append(matcher(value, full_text, lines))
        else:
            results.append(match_generic_fuzzy(field, value, full_text, lines))

    overall = _summarize(results)
    return results, overall


def _summarize(results):
    if any(r["status"] in (MISMATCH, NOT_FOUND) for r in results):
        return "fail"
    if any(r["status"] == REVIEW for r in results):
        return "needs_review"
    return "pass"
