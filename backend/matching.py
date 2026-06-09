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
    scored = [(ln, fuzz.token_set_ratio(needle, ln)) for ln in lines]
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
    """Class/type, producer, country of origin — fuzzy text presence check."""
    found_line, line_score = _best_line(expected, lines)
    return _match_fuzzy_core(field, expected, full_text, found_line, line_score)


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
    "13.5% ALC/VOL" should both satisfy an expected "13.5".
    """
    want = _parse_number(expected)
    found_numbers = _find_percentages(full_text)
    if want is None:
        return _result("alcohol_content", REVIEW, expected, None, 0,
                       "Expected ABV value could not be parsed.")
    for num, raw in found_numbers:
        if abs(num - want) < 0.05:
            return _result("alcohol_content", PASS, expected, raw, 100,
                           f"ABV matches ({raw}).")
    if found_numbers:
        nearest = min(found_numbers, key=lambda x: abs(x[0] - want))
        return _result("alcohol_content", MISMATCH, expected, nearest[1], 60,
                       f"Label shows {nearest[1]}, application says {expected}.")
    return _result("alcohol_content", NOT_FOUND, expected, None, 0,
                   "No alcohol percentage found on the label.")


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
    return _result("government_warning", NOT_FOUND, expected, None, score,
                   "Required government warning statement not found.")


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
