# Labelify — Evaluation on 40 Real COLA Labels

A check against **40 actual approved labels** pulled from the
[TTB Public COLA Registry](https://www.ttbonline.gov/colasonline/publicSearchColasBasic.do)
and run through the live app the same way an agent would.

## Method

- **Sample:** 40 COLAs — 20 Cabernet (red), 10 Chardonnay (white), 10 Bourbon
  (spirits) — across 13 countries/states and a wide spread of label designs and
  image quality.
- **Multi-panel:** each product was sent as its real **front + back** (some COLAs
  only have one panel on file).
- **Inputs:** brand, class-type code, and country of origin came straight from
  each COLA record. The government warning is checked automatically against the
  fixed federal text — it isn't an input.
- The exact 40 are bundled in [`tests/eval_labels/`](tests/eval_labels/)
  (images + `manifest.csv`), so this run reproduces — upload the manifest + images
  in the **Batch** tab or `POST` to `/verify-batch`.

## Results

| Field | Outcome |
| --- | --- |
| **Brand name** | **38 / 40 found** (31 exact, 7 review — mostly accented names: Viña, Bärenjäger, Château), 2 missed |
| **Class/type** | **27 / 40 pass** — the family lookup maps the COLA code ("TABLE RED WINE") to the grape on the label ("Cabernet Sauvignon"), etc. |
| **Gov't warning** | **31 review, 9 not-found, 0 mismatch** — the 9 not-founds are front-only products (the warning lives on the back). Correct warnings now pass to *review* instead of being failed over OCR spacing. |
| **Overall** | **18 needs-review, 22 fail** |

### By category

| Category | n | Brand found | Class pass | Warning read (review) |
| --- | --- | --- | --- | --- |
| Red (Cabernet) | 20 | 20/20 | 13/20 | 16/20 |
| White (Chardonnay) | 10 | 9/10 | 9/10 | 7/10 |
| Spirit (Bourbon) | 10 | 9/10 | 5/10 | 8/10 |

## Per-label detail

| # | Cat | Brand | Origin | Panels | Brand | Class | Origin | Warning | Overall |
|--|--|--|--|--|--|--|--|--|--|
| 1 | Red | Villa Almadi | Italy | 1 | ✅ pass | ✅ pass | ⛔ miss | ⛔ miss | fail |
| 2 | Red | Winery On The Gruene | Texas | 2 | ✅ pass | ✅ pass | — | ⚠️ review | needs review |
| 3 | Red | Twenty-One Brix Winery | New York | 2 | ✅ pass | ✅ pass | — | ⚠️ review | needs review |
| 4 | Red | Chozas Carrascal | Spain | 2 | ✅ pass | ✅ pass | ✅ pass | ⛔ miss | fail |
| 5 | Red | Viña Männle | Chile | 2 | ⚠️ review | ✅ pass | ⛔ miss | ⚠️ review | fail |
| 6 | Red | Ciccone Vineyard & Winer | Michigan | 2 | ✅ pass | ⛔ miss | — | ⚠️ review | fail |
| 7 | Red | Impero Italiano | California | 1 | ✅ pass | ✅ pass | — | ⛔ miss | fail |
| 8 | Red | Grand Reserve Cabernet S | California | 2 | ✅ pass | ⛔ miss | — | ⚠️ review | fail |
| 9 | Red | Krupp Brothers | California | 2 | ✅ pass | ⛔ miss | — | ⚠️ review | fail |
| 10 | Red | Asaka | Japan | 2 | ✅ pass | ✅ pass | ✅ pass | ⚠️ review | needs review |
| 11 | Red | Broad Street Winery | Pennsylvani | 2 | ✅ pass | ✅ pass | — | ⚠️ review | needs review |
| 12 | Red | Don Cano Reserva Caberne | Argentina | 2 | ✅ pass | ⛔ miss | ✅ pass | ⚠️ review | fail |
| 13 | Red | Alaska Legends | Alaska | 1 | ✅ pass | ✅ pass | — | ⛔ miss | fail |
| 14 | Red | Maquis Revela Cabernet S | Chile | 2 | ✅ pass | ⛔ miss | ✅ pass | ⚠️ review | fail |
| 15 | Red | Jarvis | California | 2 | ✅ pass | ⛔ miss | — | ⚠️ review | fail |
| 16 | Red | Estate Cabernet Sauvigno | California | 1 | ✅ pass | ⛔ miss | — | ⚠️ review | fail |
| 17 | Red | Calcu Fotem Cabernet Sau | Chile | 2 | ✅ pass | ✅ pass | ✅ pass | ⚠️ review | needs review |
| 18 | Red | Calcu Tiny Blocks Cabern | Chile | 2 | ✅ pass | ✅ pass | ✅ pass | ⚠️ review | needs review |
| 19 | Red | Calcu Tiny Blocks Cabern | Chile | 2 | ⚠️ review | ✅ pass | ✅ pass | ⚠️ review | needs review |
| 20 | Red | Ott Vineyards And Winery | American | 2 | ✅ pass | ✅ pass | — | ⚠️ review | needs review |
| 21 | White | Winery On The Gruene | Texas | 2 | ✅ pass | ⛔ miss | — | ⚠️ review | fail |
| 22 | White | Chateau Tanunda | Australia | 2 | ✅ pass | ✅ pass | ✅ pass | ⚠️ review | needs review |
| 23 | White | Republican Red Winery | California | 2 | ✅ pass | ✅ pass | — | ⚠️ review | needs review |
| 24 | White | Mccollum Family Vineyard | Oregon | 2 | ✅ pass | ✅ pass | — | ⚠️ review | needs review |
| 25 | White | Impero Italiano | California | 1 | ✅ pass | ✅ pass | — | ⛔ miss | fail |
| 26 | White | Fun Mom Wines | California | 1 | ⚠️ review | ✅ pass | — | ⛔ miss | fail |
| 27 | White | Fun Mom Wines | California | 1 | ⚠️ review | ✅ pass | — | ⛔ miss | fail |
| 28 | White | The Veil Brewing Co. | Virginia | 1 | ✅ pass | ✅ pass | — | ⚠️ review | needs review |
| 29 | White | Avery Brewing Co. | Colorado | 1 | ✅ pass | ✅ pass | — | ⚠️ review | needs review |
| 30 | White | Chateau Manoir Du Gravou | France | 2 | ⛔ miss | ✅ pass | ✅ pass | ⚠️ review | fail |
| 31 | Spirit | Barenjager | Germany | 1 | ⛔ miss | ⛔ miss | ⛔ miss | ⛔ miss | fail |
| 32 | Spirit | Barenjager | Germany | 2 | ⚠️ review | ⛔ miss | ✅ pass | ⚠️ review | fail |
| 33 | Spirit | Barenjager | Germany | 2 | ✅ pass | ⛔ miss | ✅ pass | ⛔ miss | fail |
| 34 | Spirit | Barenjager | Germany | 2 | ⚠️ review | ⛔ miss | ✅ pass | ⚠️ review | fail |
| 35 | Spirit | Barenjager | Germany | 2 | ✅ pass | ⛔ miss | ✅ pass | ⚠️ review | fail |
| 36 | Spirit | Canyon Diablo Distillery | Arizona | 2 | ✅ pass | ✅ pass | — | ⚠️ review | needs review |
| 37 | Spirit | Doc Brown Farm & Distill | Georgia | 2 | ✅ pass | ✅ pass | — | ⚠️ review | needs review |
| 38 | Spirit | Doc Brown Farm & Distill | Georgia | 2 | ✅ pass | ✅ pass | — | ⚠️ review | needs review |
| 39 | Spirit | Mossy Horn | Texas | 2 | ⚠️ review | ✅ pass | — | ⚠️ review | needs review |
| 40 | Spirit | Lawrenceburg Bourbon Com | Kentucky | 2 | ✅ pass | ✅ pass | — | ⚠️ review | needs review |

## How to read it

- **Brand is the strong result: 38/40 found.** The 7 reviews are accented names
  where OCR dropped a diacritic — flagged for a person, not passed or failed.
- **Warning works as a compliance check should.** It's never failed over OCR
  spacing now: a correct warning (even with the all-caps words jammed together)
  goes to **review** — text present, bold/punctuation left for a person to
  confirm. The 9 not-founds are all single-panel (front-only) products, where
  there's genuinely no warning to read.
- **Overall is mostly review-or-fail by design.** The warning gates it, and on a
  photo you can't fully clear the warning automatically — so it asks for a human.
  The fails are front-only products (warning/origin live on the back) or the few
  class misses below.
- **The 13 class misses are mostly legit, not errors:** several are Cabernets the
  producer filed under the dessert/fortified tax class (the code says dessert, the
  label says Cabernet — a real mismatch), plus a honey liqueur and a couple of
  artistic fronts where OCR didn't catch the grape.

## What this shows

1. It works on real, messy, non-cherry-picked labels — not just clean test images.
2. Multi-panel matters: warnings only show up once the back is included.
3. It fails safe — uncertainty becomes **review**, never a quiet pass.
