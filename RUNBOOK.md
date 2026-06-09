# Labelify — Run Book

Step-by-step to set up, run, and **test every feature yourself**. Commands are
Windows PowerShell (the dev environment); swap `.venv\Scripts\activate` for
`source .venv/bin/activate` on macOS/Linux. Each step lists what you should see.

> Live app (no setup needed): **https://tgarver-gdm-ttb-labelify.hf.space**

---

## 0. Prerequisites
- Python 3.11+ (`python --version`)
- ~1 GB free disk (the OCR model downloads on first run)

## 1. Get the code & install
```powershell
git clone https://github.com/tgarver-gdm/Labelify.git
cd Labelify
python -m venv .venv
.venv\Scripts\activate
pip install -r backend\requirements.txt
```
**Expect:** dependencies install, including `rapidocr-onnxruntime` and `fastapi`.

## 2. Run the unit tests (proves the matching logic — no images needed)
```powershell
pytest -q
```
**Expect:** `24 passed`. These cover every field rule (brand case-flag, ABV
ranges, class-family mapping, warning partial-detection, batch manifest parsing).

## 3. Generate a sample label image (optional, for the Single demo)
```powershell
python scripts\make_sample_label.py
```
**Expect:** `Wrote ...\tests\sample_data\sample_label.png` — a synthetic wine
label whose data matches `tests\sample_data\sample_application.json`.

## 4. Start the app
```powershell
uvicorn app:app --app-dir backend
```
**Expect:** `Uvicorn running on http://127.0.0.1:8000`. First request loads the
OCR model (a few seconds), then it's fast. Open **http://localhost:8000**.

> Quick UI check with **no OCR model**: stop the server and run
> `$env:OCR_PROVIDER="mock"; uvicorn app:app --app-dir backend` — uploads return
> canned text so you can exercise the UI instantly. Unset with `Remove-Item Env:OCR_PROVIDER`.

---

## 5. Test SINGLE mode (browser)
1. **Single label** tab → drop a photo into the **Front** slot. Use either the
   generated `tests\sample_data\sample_label.png` or the real
   `tests\sample_data\real_stone_imperial_whiskey_back.png`.
2. Fill the fields (for the Stone label: Brand `STONE`, Class `Whisky`).
3. Click **Verify label**.

**Expect (synthetic sample):** Brand ✅, Class ✅ (red wine), ABV ✅, Net contents ✅,
Government warning ⚠️ review (present + all-caps; bold needs a human).
**Expect (Stone real label):** Brand ✅, Class ⚠️/✅, warning ⚠️ partial — a
deliberately hard low-contrast label. Expand **Show raw OCR text** to see what
was read.

## 6. Test SINGLE mode (API directly)
Use real `curl.exe` (not the PowerShell alias):
```powershell
curl.exe -s -X POST http://localhost:8000/verify `
  -F "images=@tests/sample_data/real_stone_imperial_whiskey_back.png" `
  -F "brand_name=STONE" -F "class_type=Whisky"
```
**Expect:** JSON with `"overall"` and a `results` array; `brand_name` → `pass`,
`government_warning` → `review`. (The warning is checked against the fixed
federal text automatically — you don't pass it.)

## 7. Test MULTI-PANEL (front + back together)
```powershell
curl.exe -s -X POST http://localhost:8000/verify `
  -F "images=@tests/sample_data/real_twentyonebrix_cabfranc_front.png" `
  -F "images=@tests/sample_data/real_twentyonebrix_cabfranc_back.png" `
  -F "brand_name=Twenty-One Brix" -F "class_type=Red Wine"
```
**Expect:** `"image_count": 2`; brand from the front + warning from the back both
evaluated against the combined text.

---

## 8. Test BATCH mode (browser)
1. **Batch (importers)** tab → **Download a template** to see the CSV format.
2. **Manifest** → choose `tests\sample_data\batch_manifest_example.csv`.
3. **Label images** → select all four bundled images:
   `real_twentyonebrix_cabfranc_front.png`, `real_twentyonebrix_cabfranc_back.png`,
   `real_vina_mannle_back.png`, `real_stone_imperial_whiskey_back.png`.
4. Click **Verify batch**.

**Expect:** a 3-row table — `TWENTYONEBRIX` (2 panels, REVIEW),
`VINAMANNLE` (1 panel, FAIL), `STONE` (1 panel, REVIEW) — with summary chips
`REVIEW: 2 · FAIL: 1`. Twenty-One Brix correctly pulls its **two** panels.

## 9. Test BATCH mode (API directly)
```powershell
cd tests\sample_data
curl.exe -s -X POST http://localhost:8000/verify-batch `
  -F "manifest=@batch_manifest_example.csv" `
  -F "images=@real_twentyonebrix_cabfranc_front.png" `
  -F "images=@real_twentyonebrix_cabfranc_back.png" `
  -F "images=@real_vina_mannle_back.png" `
  -F "images=@real_stone_imperial_whiskey_back.png"
cd ..\..
```
**Expect:** JSON `{ "count": 3, "summary": {...}, "products": [...] }`, one entry
per manifest row with `panel_count` and per-field `results`.

---

## 10. Verify the live deployment
```powershell
curl.exe -s https://tgarver-gdm-ttb-labelify.hf.space/health
```
**Expect:** `{"status":"ok","ocr_provider":"rapidocr"}`. The live UI behaves
exactly as steps 5–9.

## 11. Run in Docker (mirrors the deployed container)
```powershell
docker build -t labelify .
docker run -p 8000:8000 labelify
```
**Expect:** same app on http://localhost:8000, self-contained (no external calls).

---

## Pull more real test labels (TTB Public COLA Registry)
1. Search: `https://www.ttbonline.gov/colasonline/publicSearchColasBasic.do`
2. Open a result → **Printable Version** → right-click the label image → **Save
   image as**. (The image servlet needs the browser session, so direct links
   won't download.)
3. Use the saved image(s) in Single or add a row to a batch manifest. The COLA
   detail page also lists the application data (brand, class, etc.) to enter.

## Troubleshooting
| Symptom | Fix |
| --- | --- |
| `Form data requires "python-multipart"` | `pip install python-multipart` (it's in requirements; ensure the venv is active) |
| First `/verify` is slow | OCR model downloads/loads once on first use; subsequent calls are fast |
| `curl` flags behave oddly in PowerShell | Use `curl.exe`, not the `curl`→`Invoke-WebRequest` alias |
| Port 8000 busy | `uvicorn app:app --app-dir backend --port 8001` |
| Just want to click around the UI | `$env:OCR_PROVIDER="mock"` before `uvicorn` |
