"""
Batch manifest parsing — for high-volume importers (Sarah's request).

A batch is a manifest (CSV or JSON) with one row per product. Each row carries
the application fields plus the filenames of that product's label panels, which
are uploaded alongside. This module just turns the manifest text into structured
products; it does no OCR or HTTP, so it's pure and unit-testable.

CSV is the primary format because importers work in spreadsheets. The `images`
column lists this product's panel filenames separated by ';' or '|'.

Example CSV:

    id,images,brand_name,class_type,alcohol_content,net_contents,country_of_origin
    P1,p1_front.jpg;p1_back.jpg,Stone's Throw,Red Wine,13.5%,750 mL,
    P2,p2.jpg,Acme,White Wine,12%,750 mL,France

The government warning is never in the manifest — it's a fixed legal constant
the app always checks (see matching.DEFAULT_GOVERNMENT_WARNING).
"""

import csv
import io
import json
import re

# Application fields a manifest row may supply (warning is excluded by design).
FIELD_KEYS = [
    "brand_name", "class_type", "alcohol_content", "net_contents",
    "producer_name_address", "country_of_origin",
]


def parse_manifest(text):
    """
    Parse manifest text (CSV or JSON array) into a list of products:
        {"id": str, "images": [filename, ...], "expected": {field: value, ...}}
    Only non-empty fields are kept in `expected`.
    """
    text = text.lstrip("﻿").strip()
    if text.startswith("["):
        rows = json.loads(text)
    else:
        rows = list(csv.DictReader(io.StringIO(text)))

    products = []
    for i, raw in enumerate(rows):
        row = {(k or "").strip().lower(): v for k, v in raw.items()}

        pid = _s(row.get("id") or row.get("product_id")) or f"row{i + 1}"

        images_cell = row.get("images") if row.get("images") is not None else row.get("image")
        if isinstance(images_cell, list):
            images = [_s(x) for x in images_cell if _s(x)]
        else:
            images = [s.strip() for s in re.split(r"[;|]", _s(images_cell)) if s.strip()]

        expected = {k: _s(row.get(k)) for k in FIELD_KEYS if _s(row.get(k))}
        products.append({"id": pid, "images": images, "expected": expected})
    return products


def _s(v):
    return "" if v is None else str(v).strip()
