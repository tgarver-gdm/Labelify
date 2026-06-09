"""
Unit tests for the matching core. These run with NO image and NO OCR model —
they feed in label text directly, so they're fast and deterministic. This is
where the verification logic is actually proven correct.

Run:  pytest -q   (from the project root, after `pip install -r backend/requirements.txt`)
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from matching import verify_fields, PASS, REVIEW, MISMATCH, NOT_FOUND

GOV = ("GOVERNMENT WARNING: (1) According to the Surgeon General, women should not "
       "drink alcoholic beverages during pregnancy because of the risk of birth defects. "
       "(2) Consumption of alcoholic beverages impairs your ability to drive a car or "
       "operate machinery, and may cause health problems.")

# A realistic OCR dump of a good label.
GOOD_LABEL = f"""STONE'S THROW
Red Wine
Napa Valley, California
Alc. 13.5% by Vol
750 mL
Acme Winery, Napa CA
{GOV}"""


def status_for(results, field):
    return next(r["status"] for r in results if r["field"] == field)


def test_exact_brand_passes():
    results, _ = verify_fields(GOOD_LABEL, {"brand_name": "STONE'S THROW"})
    assert status_for(results, "brand_name") == PASS


def test_brand_case_difference_is_flagged_not_passed():
    # Dave's nuance: same letters, different case => REVIEW, not silent PASS.
    results, _ = verify_fields(GOOD_LABEL, {"brand_name": "Stone's Throw"})
    brand = next(r for r in results if r["field"] == "brand_name")
    assert brand["status"] == REVIEW
    # Regression: case-insensitive line search must surface the ACTUAL brand line
    # (not a random line like the warning's trailing "problems."). This was a live
    # bug — rapidfuzz is case-sensitive by default.
    assert brand["found"] == "STONE'S THROW"


def test_abv_matches_despite_formatting():
    results, _ = verify_fields(GOOD_LABEL, {"alcohol_content": "13.5%"})
    assert status_for(results, "alcohol_content") == PASS


def test_abv_mismatch_detected():
    results, _ = verify_fields(GOOD_LABEL, {"alcohol_content": "12.0%"})
    assert status_for(results, "alcohol_content") == MISMATCH


def test_abv_range_on_label_passes_when_inside():
    # 27 CFR 4.36 permits a stated range; 13.5 falls inside "12% to 14%".
    label = "STONE'S THROW\nRed Wine\n12% to 14% Alc by Vol\n750 mL"
    results, _ = verify_fields(label, {"alcohol_content": "13.5%"})
    assert status_for(results, "alcohol_content") == PASS


def test_table_wine_is_legal_alternative_for_low_abv():
    label = "STONE'S THROW\nCalifornia Table Wine\n750 mL"
    results, _ = verify_fields(label, {"alcohol_content": "12.5%"})
    assert status_for(results, "alcohol_content") == REVIEW


def test_net_contents_spacing_tolerant():
    results, _ = verify_fields(GOOD_LABEL, {"net_contents": "750mL"})
    assert status_for(results, "net_contents") == PASS


def test_net_contents_mismatch():
    results, _ = verify_fields(GOOD_LABEL, {"net_contents": "700 mL"})
    assert status_for(results, "net_contents") == MISMATCH


def test_government_warning_allcaps_passes_review():
    results, _ = verify_fields(GOOD_LABEL, {"government_warning": GOV})
    # PASS-equivalent but flagged REVIEW because bold can't be OCR-verified.
    assert status_for(results, "government_warning") == REVIEW


def test_government_warning_not_allcaps_flagged():
    lower_label = GOOD_LABEL.replace(GOV, GOV.lower())
    results, _ = verify_fields(lower_label, {"government_warning": GOV})
    assert status_for(results, "government_warning") == MISMATCH


def test_government_warning_missing():
    results, _ = verify_fields("STONE'S THROW\nRed Wine", {"government_warning": GOV})
    assert status_for(results, "government_warning") == NOT_FOUND


def test_government_warning_partial_ocr_is_review_not_missing():
    # Real-world case (Stone Imperial Whiskey): tiny low-contrast print, OCR
    # garbles the warning below the exact-match threshold but still reads several
    # distinctive phrases. Should be REVIEW (verify manually), not NOT_FOUND.
    garbled = (
        "ALCOHOLIC BEVERAGESDURING PREGNA\n"
        "BECAUSE OF THE RISK OF BIRTH DEFECTS.\n"
        "YOURABILITYTO DRIVEACAROROPERATI\n"
        "MACHINERY, AND MAY CAUSE HEALTH PROBLEMS"
    )
    results, _ = verify_fields(garbled, {"government_warning": GOV})
    assert status_for(results, "government_warning") == REVIEW


def test_only_filled_fields_are_checked():
    results, _ = verify_fields(GOOD_LABEL, {"brand_name": "STONE'S THROW", "class_type": ""})
    assert len(results) == 1


def test_multi_panel_combined_text_satisfies_all_fields():
    # The multi-image rationale at the logic level: real labels split mandatory
    # info across panels. Brand/class live on the FRONT, the warning on the BACK.
    # The app OCRs each panel and joins the text (front + "\n\n" + back); neither
    # panel alone would pass, but the combined text does.
    front = "STONE'S THROW\nRed Wine\n750 mL"
    back = f"Acme Winery, Napa CA\nAlc. 13.5% by Vol\n{GOV}"
    combined = front + "\n\n" + back
    results, overall = verify_fields(combined, {
        "brand_name": "STONE'S THROW",       # front only
        "government_warning": GOV,            # back only
    })
    assert status_for(results, "brand_name") == PASS
    assert status_for(results, "government_warning") == REVIEW
