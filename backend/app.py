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
from matching import verify_fields

app = FastAPI(title="TTB Label Verification")

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


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
    government_warning: str = Form(""),
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
        "government_warning": government_warning,
    }

    results, overall = verify_fields(ocr_text, expected)
    return {"overall": overall, "results": results,
            "ocr_text": ocr_text, "image_count": len(images)}


# Serve the frontend. Mounted last so it doesn't shadow the API routes.
@app.get("/")
def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
