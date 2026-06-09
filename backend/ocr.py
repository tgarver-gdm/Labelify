"""
OCR provider — the 'vision' half of the app: turn a label photo into text.

Design choice: this is behind a tiny interface so the model is swappable and so
the rest of the app (and tests) never depend on a heavy ML library. The default
is RapidOCR: it runs fully locally (no outbound API calls — satisfies the
network constraint), installs with plain `pip` on Windows/Mac/Linux, and uses
ONNX models tuned for rotated/low-quality photos.

Set OCR_PROVIDER=mock to run the whole app with no OCR installed (useful for
demos and UI work).
"""

import os
import io


class MockOCR:
    """Returns whatever text is embedded; lets the app run with zero ML deps."""
    def extract_text(self, image_bytes: bytes) -> str:
        return os.environ.get(
            "MOCK_OCR_TEXT",
            "MOCK MODE — set OCR_PROVIDER=rapidocr and upload a real label.",
        )


class RapidOCR:
    """Local ONNX OCR. Lazy-loaded so importing this module stays cheap."""
    def __init__(self):
        from rapidocr_onnxruntime import RapidOCR as _Engine
        self._engine = _Engine()

    def extract_text(self, image_bytes: bytes) -> str:
        from PIL import Image
        import numpy as np
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        result, _ = self._engine(np.array(img))
        if not result:
            return ""
        # result is a list of [box, text, confidence]; keep reading order.
        return "\n".join(line[1] for line in result)


_provider = None


def get_ocr():
    global _provider
    if _provider is None:
        name = os.environ.get("OCR_PROVIDER", "rapidocr").lower()
        _provider = MockOCR() if name == "mock" else RapidOCR()
    return _provider
