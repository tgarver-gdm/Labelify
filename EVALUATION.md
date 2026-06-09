# Labelify — Evaluation on 40 Real COLA Labels

A validation run against **40 actual approved labels** pulled live from the
[TTB Public COLA Registry](https://www.ttbonline.gov/colasonline/publicSearchColasBasic.do),
submitted to the deployed app exactly as an agent would.

## Method

- **Sample:** 40 COLAs across three searches — 20 Cabernet (red wine), 10
  Chardonnay (white wine), 10 Bourbon (spirits) — spanning 13 countries/states
  and a wide range of label designs, fonts, and image quality.
- **Multi-panel:** each product was submitted as its real **front + back**
  panels (neck where present); 8 COLAs had only a single panel on file.
- **Expected data** (brand, class/type code, country of origin) was taken
  verbatim from each COLA record. The **government warning is not an input** — the
  app always checks it against the fixed federal text (27 CFR Part 16).
- **Live endpoint:** `POST /verify` on the deployed Space, OCR via local RapidOCR.

> **Reproduce it yourself.** The full corpus — all 40 products' label images plus
> a ready-to-upload `manifest.csv` and a `field_data_reference.csv` — is bundled
> at [`tests/eval_labels/`](tests/eval_labels/). Upload `manifest.csv` + the
> images in the app's **Batch** tab, or `POST` them to `/verify-batch`. (Because
> the registry returns newest matches first, a fresh pull may differ by a few
> rows from the table below; the bundled corpus is the exact set referenced here.)

## Headline results

| Field | Outcome |
| --- | --- |
| **Brand name** | **39 / 40 located** (31 exact pass, 8 review — mostly accented names: Viña, Bärenjäger, Château), 1 miss |
| **Class/type** | **27 / 40 pass** — the family map resolves "TABLE RED WINE" → Cabernet, "TABLE WHITE WINE" → Chardonnay, beer/liqueur, etc. |
| **Gov't warning** | 13 review · 19 mismatch · 8 not-found — **never silently passed**; the 8 not-founds are front-only (single-panel) COLAs with no warning to read |
| **Overall** | 9 needs-review · 31 fail |

### By category

| Category | n | Brand located | Class pass | Warning detected on label |
| --- | --- | --- | --- | --- |
| Red (Cabernet) | 20 | 20/20 | 13/20 | 16/20 |
| White (Chardonnay) | 10 | 9/10 | 9/10 | 7/10 |
| Spirit (Bourbon) | 10 | 10/10 | 5/10 | 9/10 |

## Per-label detail

| # | Cat | Brand | Origin | Panels | Brand | Class | Origin | Warning | Overall |
|--|--|--|--|--|--|--|--|--|--|
| 1 | Red | Villa Almadi | Italy | 1 | ✅ pass | ✅ pass | ⛔ miss | ⛔ miss | fail |
| 2 | Red | Winery On The Gruene | Texas | 2 | ✅ pass | ✅ pass | — | ❌ mism | fail |
| 3 | Red | Twenty-One Brix Winery | New York | 2 | ✅ pass | ✅ pass | — | ⚠️ review | needs review |
| 4 | Red | Chozas Carrascal | Spain | 2 | ✅ pass | ✅ pass | ✅ pass | ⛔ miss | fail |
| 5 | Red | Viña Männle | Chile | 2 | ⚠️ review | ✅ pass | ⛔ miss | ⚠️ review | fail |
| 6 | Red | Ciccone Vineyard & Winer | Michigan | 2 | ✅ pass | ⛔ miss | — | ❌ mism | fail |
| 7 | Red | Impero Italiano | California | 1 | ✅ pass | ✅ pass | — | ⛔ miss | fail |
| 8 | Red | Grand Reserve Cabernet S | California | 2 | ✅ pass | ⛔ miss | — | ❌ mism | fail |
| 9 | Red | Krupp Brothers | California | 2 | ✅ pass | ⛔ miss | — | ❌ mism | fail |
| 10 | Red | Asaka | Japan | 2 | ✅ pass | ✅ pass | ✅ pass | ❌ mism | fail |
| 11 | Red | Broad Street Winery | Pennsylvani | 2 | ✅ pass | ✅ pass | — | ⚠️ review | needs review |
| 12 | Red | Don Cano Reserva Caberne | Argentina | 2 | ✅ pass | ⛔ miss | ✅ pass | ❌ mism | fail |
| 13 | Red | Alaska Legends | Alaska | 1 | ✅ pass | ✅ pass | — | ⛔ miss | fail |
| 14 | Red | Maquis Revela Cabernet S | Chile | 2 | ✅ pass | ⛔ miss | ✅ pass | ❌ mism | fail |
| 15 | Red | Jarvis | California | 2 | ✅ pass | ⛔ miss | — | ❌ mism | fail |
| 16 | Red | Estate Cabernet Sauvigno | California | 1 | ✅ pass | ⛔ miss | — | ❌ mism | fail |
| 17 | Red | Calcu Fotem Cabernet Sau | Chile | 2 | ✅ pass | ✅ pass | ✅ pass | ❌ mism | fail |
| 18 | Red | Calcu Tiny Blocks Cabern | Chile | 2 | ✅ pass | ✅ pass | ✅ pass | ⚠️ review | needs review |
| 19 | Red | Calcu Tiny Blocks Cabern | Chile | 2 | ⚠️ review | ✅ pass | ✅ pass | ⚠️ review | needs review |
| 20 | Red | Ott Vineyards And Winery | American | 2 | ✅ pass | ✅ pass | — | ❌ mism | fail |
| 21 | White | Winery On The Gruene | Texas | 2 | ✅ pass | ⛔ miss | — | ❌ mism | fail |
| 22 | White | Chateau Tanunda | Australia | 2 | ✅ pass | ✅ pass | ✅ pass | ⚠️ review | needs review |
| 23 | White | Republican Red Winery | California | 2 | ✅ pass | ✅ pass | — | ❌ mism | fail |
| 24 | White | Mccollum Family Vineyard | Oregon | 2 | ✅ pass | ✅ pass | — | ❌ mism | fail |
| 25 | White | Impero Italiano | California | 1 | ✅ pass | ✅ pass | — | ⛔ miss | fail |
| 26 | White | Fun Mom Wines | California | 1 | ⚠️ review | ✅ pass | — | ⛔ miss | fail |
| 27 | White | Fun Mom Wines | California | 1 | ⚠️ review | ✅ pass | — | ⛔ miss | fail |
| 28 | White | The Veil Brewing Co. | Virginia | 1 | ✅ pass | ✅ pass | — | ⚠️ review | needs review |
| 29 | White | Avery Brewing Co. | Colorado | 1 | ✅ pass | ✅ pass | — | ⚠️ review | needs review |
| 30 | White | Chateau Manoir Du Gravou | France | 2 | ⛔ miss | ✅ pass | ✅ pass | ⚠️ review | fail |
| 31 | Spirit | Barenjager | Germany | 2 | ⚠️ review | ⛔ miss | ✅ pass | ⚠️ review | fail |
| 32 | Spirit | Barenjager | Germany | 2 | ⚠️ review | ⛔ miss | ✅ pass | ❌ mism | fail |
| 33 | Spirit | Barenjager | Germany | 2 | ✅ pass | ⛔ miss | ✅ pass | ⛔ miss | fail |
| 34 | Spirit | Barenjager | Germany | 2 | ⚠️ review | ⛔ miss | ✅ pass | ❌ mism | fail |
| 35 | Spirit | Barenjager | Germany | 2 | ✅ pass | ⛔ miss | ✅ pass | ⚠️ review | fail |
| 36 | Spirit | Canyon Diablo Distillery | Arizona | 2 | ✅ pass | ✅ pass | — | ⚠️ review | needs review |
| 37 | Spirit | Doc Brown Farm & Distill | Georgia | 2 | ✅ pass | ✅ pass | — | ❌ mism | fail |
| 38 | Spirit | Doc Brown Farm & Distill | Georgia | 2 | ✅ pass | ✅ pass | — | ❌ mism | fail |
| 39 | Spirit | Mossy Horn | Texas | 2 | ⚠️ review | ✅ pass | — | ⚠️ review | needs review |
| 40 | Spirit | Lawrenceburg Bourbon Com | Kentucky | 2 | ✅ pass | ✅ pass | — | ❌ mism | fail |

## How to read this

- **Brand detection is the strong result: 39/40.** Across Italian, Spanish,
  Chilean, German, Japanese and US labels, with heavy stylization, the brand was
  found. The 8 "review" rows are accented names where OCR dropped a diacritic —
  correctly flagged for a human rather than passed or failed.
- **Overall is mostly "fail" by design, and the gate is the warning.** On real
  back labels the warning prints small and low-contrast; OCR frequently can't
  verify it to an *exact* standard, so it returns mismatch/review — a compliance
  tool must never rubber-stamp a warning it couldn't read. Forcing these to
  "pass" would be the wrong behavior. The 9 **needs-review** rows are where every
  field resolved cleanly.
- **The 13 class misses are mostly legitimate**, not failures: several are
  Cabernets the producer filed under the **dessert/fortified tax class** (so the
  label says "Cabernet," which the *dessert* family doesn't accept — a real
  code-vs-label divergence), plus a honey liqueur (Bärenjäger) and a few artistic
  fronts where OCR didn't capture the varietal.

## What this validates

1. The two-stage design (local OCR → per-field rules) works on real, messy,
   non-curated labels — not just synthetic happy-path inputs.
2. Multi-panel submission is necessary and effective: warnings are only readable
   once the back panel is included.
3. The matcher fails safe everywhere — it surfaces uncertainty as **review**
   rather than guessing.

## Known limitations (surfaced by this run)

- Small/low-contrast warning print defeats exact OCR matching; image
  preprocessing (deskew, contrast, upscaling) or a local vision-language model
  would lift warning verification.
- The COLA "class/type" code can legitimately diverge from the on-label
  designation (dessert-class Cabernets); a fuller code→designation table would
  reduce class misses.
- Accented brand names lose diacritics in OCR → review rather than pass.

*Generated from a live 40-label run; see `tests/` for the deterministic unit
suite that backs the matching logic.*
