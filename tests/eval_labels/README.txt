Labelify — 40 real COLA label test corpus
==========================================

40 products pulled from the TTB Public COLA Registry (20 Cabernet / 10 Chardonnay
/ 10 Bourbon), each with its front and/or back label image and its application
field data. Use this to exercise Labelify's BATCH mode end to end.

FILES
-----
manifest.csv              Ready to upload. One row per product: id, image
                          filenames, and the application fields.
field_data_reference.csv  The same data plus extra context (category, TTB id,
                          origin/state, varietal/fanciful name) for your reference.
<id>_front.<ext>          Front label image(s).
<id>_back.<ext>           Back label image(s) where the COLA had one.
71 images across 40 products.

NOTES ON THE FIELD DATA
-----------------------
- brand_name, class_type, country_of_origin come straight from the COLA record.
- class_type is the TTB CATEGORY CODE (e.g. "TABLE RED WINE"); the label prints a
  varietal ("Cabernet Sauvignon"). Labelify's class-family map resolves this.
- alcohol_content, net_contents, producer_name_address are BLANK: the public
  search doesn't expose them (they live on the label image / COLA detail page).
  Fill them in from a label if you want to test those fields too.
- The government warning is NOT in the manifest — Labelify always checks it
  against the fixed federal text automatically.
- country_of_origin is set only for imports; US-domestic rows leave it blank.

HOW TO TEST — option A: live app (no setup)
-------------------------------------------
1. Open https://tgarver-gdm-ttb-labelify.hf.space  ->  "Batch (importers)" tab.
2. Manifest      -> choose manifest.csv (from this folder).
3. Label images  -> select ALL the .jpg/.png files in this folder.
4. Click "Verify batch".  You'll get a 40-row verdict table with summary chips.
   (Processing 71 images takes ~30-60s.)

HOW TO TEST — option B: API with curl
-------------------------------------
From this folder, in PowerShell (use curl.exe, not the alias):

    $imgs = Get-ChildItem *.jpg,*.png | ForEach-Object { "-F"; "images=@$($_.Name)" }
    curl.exe -s -X POST https://tgarver-gdm-ttb-labelify.hf.space/verify-batch `
      -F "manifest=@manifest.csv" @imgs

Returns JSON: { count, summary, products: [ {id, overall, panel_count, results}... ] }.

HOW TO TEST — option C: single product
--------------------------------------
Open the "Single label" tab, drop one product's front (+back) into the slots,
type its brand/class from manifest.csv, and Verify.

WHAT TO EXPECT
--------------
- Brand: passes on almost all (a couple "review" on accented names like Viña).
- Class: passes where the label shows a mappable designation; a few dessert-class
  Cabernets legitimately mismatch (code says dessert, label says Cabernet).
- Warning: review/mismatch on real low-contrast back labels, "not found" on
  front-only products — never silently passed (fail-safe by design).
- Overall is gated by the warning, so many show fail/needs-review. See
  EVALUATION.md in the repo for the full interpretation.
