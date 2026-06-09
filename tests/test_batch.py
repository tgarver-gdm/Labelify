"""
Unit tests for batch manifest parsing. Pure — no images, no OCR, no HTTP.
"""

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from batch import parse_manifest

CSV = """id,images,brand_name,class_type,alcohol_content,net_contents,country_of_origin
P1,p1_front.jpg;p1_back.jpg,Stone's Throw,Red Wine,13.5%,750 mL,
P2,p2.jpg,Acme,White Wine,12%,750 mL,France
"""


def test_csv_parses_rows_and_images():
    products = parse_manifest(CSV)
    assert [p["id"] for p in products] == ["P1", "P2"]
    assert products[0]["images"] == ["p1_front.jpg", "p1_back.jpg"]
    assert products[1]["images"] == ["p2.jpg"]


def test_only_nonempty_fields_kept():
    products = parse_manifest(CSV)
    assert products[0]["expected"]["brand_name"] == "Stone's Throw"
    # P1 has no country_of_origin -> excluded; warning is never in the manifest.
    assert "country_of_origin" not in products[0]["expected"]
    assert "government_warning" not in products[0]["expected"]
    assert products[1]["expected"]["country_of_origin"] == "France"


def test_json_manifest_supported():
    js = '[{"id":"X","images":["a.jpg","b.jpg"],"brand_name":"Foo","class_type":"Red Wine"}]'
    products = parse_manifest(js)
    assert products[0]["id"] == "X"
    assert products[0]["images"] == ["a.jpg", "b.jpg"]
    assert products[0]["expected"]["brand_name"] == "Foo"


def test_missing_id_falls_back_to_row_number():
    products = parse_manifest("images,brand_name\na.jpg,Foo\n")
    assert products[0]["id"] == "row1"
