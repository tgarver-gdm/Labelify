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
    assert status_for(results, "brand_name") == REVIEW


def test_abv_matches_despite_formatting():
    results, _ = verify_fields(GOOD_LABEL, {"alcohol_content": "13.5%"})
    assert status_for(results, "alcohol_content") == PASS


def test_abv_mismatch_detected():
    results, _ = verify_fields(GOOD_LABEL, {"alcohol_content": "12.0%"})
    assert status_for(results, "alcohol_content") == MISMATCH


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


def test_only_filled_fields_are_checked():
    results, _ = verify_fields(GOOD_LABEL, {"brand_name": "STONE'S THROW", "class_type": ""})
    assert len(results) == 1
