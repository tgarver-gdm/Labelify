"""
FastAPI app: one /verify endpoint + serves the single-page frontend.

Flow: receive one or more label images (front/back/neck) + expected field values
-> OCR each image -> combine the text -> run field matching -> return a per-field
checklist as JSON.

Multi-image matters because real COLAs split mandatory info across panels: the
brand/class sit on the FRONT while the government warning, ABV and net contents
are on the BACK. Checking a single photo can never satisfy every field, so we
accept all panels for one application and verify against their combined text.
"""

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List
import os

from ocr import get_ocr
from matching import verify_fields, DEFAULT_GOVERNMENT_WARNING
from batch import parse_manifest

app = FastAPI(title="TTB Label Verification")

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


def _verify_panels(panel_bytes, expected_overrides):
    """OCR a list of image-bytes, combine, and verify. Shared by /verify and
    /verify-batch. The warning is always the fixed federal constant."""
    ocr = get_ocr()
    texts = [ocr.extract_text(b) for b in panel_bytes]
    ocr_text = "\n\n".join(texts)
    expected = dict(expected_overrides)
    expected["government_warning"] = DEFAULT_GOVERNMENT_WARNING
    results, overall = verify_fields(ocr_text, expected)
    return results, overall, ocr_text


@app.get("/health")
def health():
    return {"status": "ok", "ocr_provider": os.environ.get("OCR_PROVIDER", "rapidocr")}


@app.post("/verify")
async def verify(
    images: List[UploadFile] = File(...),
    brand_name: str = Form(""),
    class_type: str = Form(""),
    alcohol_content: str = Form(""),
    net_contents: str = Form(""),
    producer_name_address: str = Form(""),
    country_of_origin: str = Form(""),
):
    # OCR every uploaded panel and combine the text. A blank line between panels
    # keeps lines from different images from being read as one (e.g. a brand on
    # the front bleeding into a warning line on the back).
    texts = []
    try:
        ocr = get_ocr()
        for img in images:
            texts.append(ocr.extract_text(await img.read()))
    except Exception as exc:  # OCR failures shouldn't 500 the agent
        return JSONResponse(
            status_code=503,
            content={"error": f"OCR failed: {exc}. Try OCR_PROVIDER=mock to test the UI."},
        )
    ocr_text = "\n\n".join(texts)

    expected = {
        "brand_name": brand_name,
        "class_type": class_type,
        "alcohol_content": alcohol_content,
        "net_contents": net_contents,
        "producer_name_address": producer_name_address,
        "country_of_origin": country_of_origin,
        # Always checked against the fixed federal text — not a form input.
        "government_warning": DEFAULT_GOVERNMENT_WARNING,
    }

    results, overall = verify_fields(ocr_text, expected)
    return {"overall": overall, "results": results,
            "ocr_text": ocr_text, "image_count": len(images)}


@app.post("/verify-batch")
async def verify_batch(
    manifest: UploadFile = File(...),
    images: List[UploadFile] = File(default=[]),
):
    """
    Batch mode for high-volume importers. Upload a CSV/JSON manifest (one row per
    product, listing its panel filenames + expected fields) plus all the label
    images. Returns a per-product verdict table. Images are matched to products
    by filename (full name or basename).
    """
    try:
        manifest_text = (await manifest.read()).decode("utf-8-sig")
        products = parse_manifest(manifest_text)
    except Exception as exc:
        return JSONResponse(status_code=400,
                            content={"error": f"Could not parse manifest: {exc}"})

    # Index uploaded images by both full filename and basename for flexible mapping.
    img_map = {}
    for img in images:
        data = await img.read()
        img_map[img.filename] = data
        img_map[os.path.basename(img.filename)] = data

    results = []
    for p in products:
        panel_bytes, missing = [], []
        for fn in p["images"]:
            data = img_map.get(fn) or img_map.get(os.path.basename(fn))
            (panel_bytes.append(data) if data is not None else missing.append(fn))

        if not panel_bytes:
            results.append({"id": p["id"], "overall": "no_images",
                            "results": [], "panel_count": 0, "missing_images": missing})
            continue
        try:
            field_results, overall, _ = _verify_panels(panel_bytes, p["expected"])
        except Exception as exc:
            results.append({"id": p["id"], "overall": "error",
                            "results": [], "panel_count": len(panel_bytes), "error": str(exc)})
            continue
        results.append({"id": p["id"], "overall": overall, "results": field_results,
                        "panel_count": len(panel_bytes), "missing_images": missing})

    summary = {}
    for r in results:
        summary[r["overall"]] = summary.get(r["overall"], 0) + 1
    return {"count": len(results), "summary": summary, "products": results}


# Serve the frontend. Mounted last so it doesn't shadow the API routes.
@app.get("/")
def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
