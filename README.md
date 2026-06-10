---
title: TTB Labelify
emoji: 🍷
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 8000
pinned: false
---

# Labelify — TTB Label Verification (Prototype)

Checks an alcohol label against the application data filed for it. Drop in the
label photos, fill in the application fields, and get a per-field pass / review /
fail list back in seconds. Works one product at a time, or a whole batch.

**The other docs:**

- 📄 [APPROACH.md](APPROACH.md) — how it works and why I built it this way
- 📊 [EVALUATION.md](EVALUATION.md) — a run on 40 real registry labels
- 🧪 [RUNBOOK.md](RUNBOOK.md) — step-by-step to test every feature yourself

This README is just the practical stuff: setup, tools, and the config knobs.

---

## Assumptions made

- **The brief shipped no sample data**, so I pulled real labels from the public
  TTB COLA Registry. The registry only has **raster label photos** (no vector/PDF
  artwork), so this is photo-based OCR, not font-metadata reading. (with that data Bold detection is possible as well as other font requirements)
- **Bold isn't verified.** OCR reads words, not how bold they are, so the warning
  is flagged for a person to confirm bold. (The reliable fix is reading the
  producer's source print file, which isn't available publicly.)
- **The warning is the same on every product** (27 CFR Part 16), so the app checks
  it against that fixed text instead of asking the agent to type it.
- **ABV and net contents aren't in the public registry's structured data** — they're only
  on the label image — so the bundled test data leaves those blank.
- Matching thresholds are sensible defaults; on a real deployment they'd be tuned
  against a labelled sample set.
- Prototype scope: no login, no pass/fail cert, no database, no audit trail.

---

## Tools used

| Tool                                  | What it does here                                                                                        |
| ------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| **Python 3.11**                       | Everything server-side                                                                                   |
| **RapidOCR** (`rapidocr-onnxruntime`) | The AI — local neural-net OCR (ONNX) that reads text off the photos. Runs on the server, no cloud calls. |
| **rapidfuzz**                         | Fuzzy string matching for the field checks (handles small OCR misreads)                                  |
| **FastAPI + Uvicorn**                 | The web server and the `/verify`, `/ocr`, `/verify-batch` endpoints                                      |
| **Pillow + NumPy**                    | Loading/handling the images before OCR                                                                   |
| **Vanilla HTML/CSS/JS**               | The single-page UI — no framework, no build step                                                         |
| **pytest**                            | Tests for the matching logic (no images needed)                                                          |
| **Docker**                            | Packaging, so it runs the same anywhere                                                                  |

No cloud APIs, no database, no auth, no build tooling. On purpose — it has to run
on an air-gapped network and stay simple.

---

## Quick start

```bash
git clone https://github.com/tgarver-gdm/Labelify.git
cd Labelify
python -m venv .venv
.venv\Scripts\activate          # Windows  (macOS/Linux: source .venv/bin/activate)
pip install -r backend/requirements.txt

uvicorn app:app --app-dir backend     # then open http://localhost:8000
```

First request downloads/loads the OCR model (a few seconds); after that it's
fast. Run the tests with `pytest -q` (they need no images or model).

---

## Configuration knobs

Everything is controlled by a couple of environment variables — no config files.

| Variable        | Default            | What it does                                                                                                            |
| --------------- | ------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| `OCR_PROVIDER`  | `rapidocr`         | OCR engine. Set to `mock` to skip real OCR and return canned text — handy for poking at the UI with no model installed. |
| `MOCK_OCR_TEXT` | a placeholder line | What `mock` mode "reads" from any image. Set it to test the field logic without real photos.                            |

Other run-time knobs:

- **Port:** `uvicorn app:app --app-dir backend --port 8001` (default 8000).
- **Hugging Face Spaces:** the `app_port: 8000` line in this README's header tells
  the Space which port the app listens on — no Dockerfile change needed.

Quick mock-mode example (Windows PowerShell):

```powershell
$env:OCR_PROVIDER="mock"; $env:MOCK_OCR_TEXT="STONE Red Wine 13.5% 750 mL"
uvicorn app:app --app-dir backend
```

---

## Project layout

```
backend/
  app.py        FastAPI: /verify, /ocr (background pre-read), /verify-batch, serves the page
  ocr.py        OCR provider (RapidOCR local; mock fallback)
  matching.py   the field checks — one rule per field
  batch.py      CSV/JSON manifest parsing for batch mode
  requirements.txt
frontend/
  index.html    single-page UI (no build step)
tests/
  test_matching.py    field-logic tests
  test_batch.py       manifest-parsing tests
  sample_data/        a few sample labels + application data
  eval_labels/        the 40-label corpus + manifest (see EVALUATION.md)
scripts/
  make_sample_label.py    generate a synthetic test label
Dockerfile
```

---

## Single vs. batch

- **Single** — one product. Three photo slots (Front / Back / Neck), fill the
  fields, Verify. Photos are read in the background as you add them, so Verify is
  near-instant.
- **Batch** — for high-volume importers. Upload a **CSV manifest** (one row per
  product: its image filenames + application fields) plus all the images, and get
  a results table. A ready example is in `tests/eval_labels/manifest.csv`, and the
  UI has a one-click template download.

---

## Data handling

Uploaded images are **not stored**. Each one is read into memory, run through OCR,
and dropped when the request finishes — nothing is written to disk, cached, or
put in a database. There's no PII sitting at rest.

---

## Deployment

It's a single Docker container (OCR needs a couple of system libraries, so Docker
keeps it consistent):

```bash
docker build -t labelify .
docker run -p 8000:8000 labelify
```

Self-contained — no outbound calls, so it works on an air-gapped network.

**Free hosting for a demo URL:**

| Host                                | Free?              | Notes                                                                                                        |
| ----------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------ |
| **Hugging Face Spaces (Docker)** ⭐ | Yes, no card       | Best fit — 16 GB RAM handles the OCR; persistent URL; this repo already has the `Dockerfile` + Space header. |
| **Render**                          | Yes, no card       | Builds from the Dockerfile; 512 MB free tier is tight for OCR; cold starts.                                  |
| **Koyeb**                           | Yes, no card       | One free Docker service.                                                                                     |
| **Google Cloud Run**                | Generous free tier | Scales to zero; needs a GCP account + card.                                                                  |

Vercel / Netlify won't work — they don't run a Python OCR container.

---

## Government web standards

For a real Treasury/TTB system these apply. What's built in vs. what's a
production step:

| Requirement | Status |
| --- | --- |
| **Section 508 / WCAG 2.1 AA** (accessibility) | **Basics built in** — keyboard-operable (photo slots work with Enter/Space, visible focus outline), labels tied to inputs, results announced to screen readers (`aria-live`), and every status uses an icon **+ text**, never color alone. A full AA audit is a production step. |
| **21st Century IDEA Act / USWDS** | Not applied — a production build would adopt the U.S. Web Design System styling. Out of scope for a prototype. |
| **Privacy Act / Privacy Impact Assessment** | The app **stores nothing** (see Data handling), so there's no PII at rest. A formal PIA is still a production step. |
| **FedRAMP / ATO, FISMA** | Hosting & authorization (Marcus noted the FedRAMP migration) — organizational, not code. Out of scope for a prototype. |
| **Plain Writing Act** | The UI uses plain language. |

Short version: the accessibility basics are in; USWDS theming, FedRAMP/ATO, and a
formal PIA are real production work a prototype can't certify — listed here so
they're not forgotten.
