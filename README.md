# Labelify — TTB Label Verification (Prototype)

An AI-assisted tool for TTB agents to verify that an alcohol beverage **label**
matches the **application data** submitted for it. Upload a label photo, confirm
the expected field values, and get a per-field pass/review/fail checklist in
seconds.

> Built for the take-home brief. Guiding principle: a **clean, working core**
> over incomplete ambitious features.

---

## How it works (30-second version)

```
label photo ──► [ OCR: read all text ]  ──►  [ match each field ]  ──► checklist
                  RapidOCR (local)            deterministic rules
```

The problem splits cleanly into two halves:

1. **Vision** — read the text off a photo taken at an angle, with glare
   (`backend/ocr.py`). Uses **RapidOCR**, an ONNX OCR engine that runs
   **entirely locally**.
2. **Logic** — compare the extracted text to the expected values, with a
   *different rule per field* (`backend/matching.py`). Pure, fast, and
   fully unit-tested without images.

### Why these choices (mapped to stakeholder constraints)

| Constraint (from the brief) | Decision |
| --- | --- |
| *"Network blocks outbound traffic… avoid cloud API dependencies"* (Marcus) | **No cloud LLM.** OCR runs locally; no outbound calls at inference time. |
| *"Results back in ~5 seconds"* (Sarah) | OCR runs once per image (~1–2s CPU); matching is plain string math (ms). Model is loaded once at startup, not per request. |
| *"My mother could figure it out"* (Sarah) | One page: drop a photo, the form is pre-filled with the fixed warning text, results are a green-✓ / red-✗ checklist. |
| *"STONE'S THROW vs Stone's Throw"* nuance (Dave) | Brand matching surfaces case/punctuation differences as **REVIEW** — it never silently passes them. |
| *Warning = exact, ALL CAPS, bold* (Jenny) | Strictest matcher. Verifies text + ALL CAPS. **Bold can't be read from OCR text**, so it's flagged for human confirmation rather than faked. |
| *Photos at angles / glare* (Jenny) | RapidOCR handles rotation; fuzzy matching tolerates minor misreads; every field shows what was read + a confidence score so low-confidence fields get human eyes. |

---

## Run it locally

```bash
cd ttb-label-verify
python -m venv .venv && . .venv/Scripts/activate        # Windows
#  source .venv/bin/activate                            # macOS/Linux
pip install -r backend/requirements.txt

# Generate a sample label image to test with (optional):
python scripts/make_sample_label.py

# Start the app:
uvicorn app:app --app-dir backend --reload
# open http://localhost:8000
```

**No OCR installed / just want to see the UI?** Run in mock mode:

```bash
#  set the text the "OCR" should return, then start with OCR_PROVIDER=mock
#  Windows PowerShell:
$env:OCR_PROVIDER="mock"; uvicorn app:app --app-dir backend
```

## Run the tests

```bash
pytest -q          # proves the matching logic, no image/model needed
```

---

## Test data

The brief shipped **no sample labels**, so:

- `scripts/make_sample_label.py` generates a synthetic wine label
  (`tests/sample_data/sample_label.png`) that matches
  `tests/sample_data/sample_application.json`. Note the application uses
  *"Stone's Throw"* while the label shows *"STONE'S THROW"* — a deliberate
  demo of the case-difference REVIEW flag.
- **Real labels:** the public **TTB COLA Public Registry**
  (ttbonline.gov → "Public COLA Registry") has thousands of real approved
  labels with their application data — ideal for realistic testing.

---

## Project layout

```
backend/
  app.py        FastAPI: /verify endpoint + serves the page
  ocr.py        OCR provider (RapidOCR local; mock fallback)
  matching.py   the verification core — one rule per field
  requirements.txt
frontend/
  index.html    single-page UI (no build step)
tests/
  test_matching.py        unit tests for the logic
  sample_data/            sample application + generated label
scripts/
  make_sample_label.py    generate a test label image
Dockerfile
```

---

## Deployment

The app is a single container (OCR needs system libs, so Docker keeps it
reproducible):

```bash
docker build -t ttb-label-verify .
docker run -p 8000:8000 ttb-label-verify
```

Deploy that image to any container host (Render / Railway / Fly.io / Azure
Container Apps). For TTB's own air-gapped network it runs self-contained — no
egress required.

---

## Assumptions & limitations (honest list)

- **Bold styling is not verified** — OCR yields text, not font weight. The
  warning is flagged for a human to confirm bold. Detecting bold reliably needs
  layout/vision analysis, out of scope for a prototype.
- Matching thresholds (88 / 72 for fuzzy fields) are sensible defaults; they'd
  be tuned against a real labelled sample set.
- One label per request in the UI. **Batch upload** (Sarah's request for
  importers) is intentionally deferred — it's the same `/verify` call in a loop
  and was left out to keep the core clean per the brief's trade-off philosophy.
- No persistence / no PII stored, per the prototype scope.

## If I had more time

Image preprocessing (deskew + contrast), threshold tuning on real labels, a
local vision-language model as a fallback for hard images, batch upload, and
saving results for audit. None of these change the two-stage architecture.
