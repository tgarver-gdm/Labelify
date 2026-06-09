# Labelify — Approach & Decisions

A short walkthrough of how I read the brief and what I chose to build. The
guiding rule throughout: **a clean, working core beats incomplete ambitious
features** (the brief's own trade-off philosophy), and **every decision should
trace back to a stakeholder constraint.**

---

## 1. How I framed the problem

The brief calls this "AI-powered," but the real shape is narrower and more
tractable than "throw it at an LLM":

> Read the text off a photo of a label, then check each required field against
> the data the producer submitted.

That splits cleanly into two independent halves:

| Half | Job | Why separate |
| --- | --- | --- |
| **Vision** | Photo → text | Hard, ML-shaped, but a solved problem (OCR). |
| **Logic** | Text → pass/fail per field | Deterministic, testable, explainable. |

Keeping them separate is the central design decision. It makes the logic
fully unit-testable without images, keeps each piece swappable, and means I can
explain *exactly* why any field passed or failed — which matters for a
compliance tool where an agent is accountable for the result.

---

## 2. Decisions mapped to stakeholders

| Constraint (who said it) | Decision | Rationale |
| --- | --- | --- |
| "Network blocks outbound traffic… avoid cloud API dependencies" — **Marcus (IT)** | **No cloud LLM/API.** OCR runs locally (RapidOCR, ONNX). | A cloud-vision call would literally fail on their network. This is the load-bearing constraint and rules out the obvious "just call GPT-4V" answer. |
| "Results back in ~5 seconds or nobody uses it" — **Sarah** | OCR once per image (~1–2s CPU); matching is plain string math (ms). Model loaded once at startup. | The only real cost is the vision step; everything after is instant. |
| "My mother could figure it out" — **Sarah** | One page: drop photos, fill only the application-specific fields, results are a green-✓ / red-✗ checklist. | Mirrors the manual checklist agents already use. Nothing to learn. |
| "STONE'S THROW vs Stone's Throw" — **Dave** | Brand matching flags case/punctuation differences as **REVIEW**, never a silent pass. | The whole point is nuance; auto-normalizing would erase exactly the signal Dave cares about. |
| Warning = exact text, ALL CAPS, bold — **Jenny** | Strictest matcher: verifies text + ALL CAPS; **flags bold for human confirmation** because OCR can't read font weight. The text is **fixed by law (27 CFR Part 16), so it's a built-in constant the app always checks — not a form field the agent types.** | Honesty over theater; and per-application input for a legally-fixed string would just invite typos. |
| Photos at angles / glare — **Jenny** | RapidOCR handles rotation; fuzzy matching tolerates minor misreads; every field shows what was read + a confidence score. | Low-confidence fields get human eyes instead of a false pass. The tool *assists*, it doesn't replace judgment. |
| Batch upload for importers — **Sarah** | Deferred (documented). | Same `/verify` call in a loop. Left out to keep the core clean, per the brief. |

---

## 3. Matching strategy — one rule per field

Treating every field the same way is the trap. Each needs its own rule:

| Field | Rule | Why |
| --- | --- | --- |
| Brand name | Fuzzy match; **case/punctuation difference → REVIEW** | Dave's nuance |
| Class/type, Producer, Origin | Fuzzy presence (token + partial ratio) | Survives OCR noise |
| **ABV** | Compare the *number*; honor stated **ranges** and **"table/light wine"** per [27 CFR 4.36](https://www.ecfr.gov/current/title-27/chapter-I/subchapter-A/part-4/subpart-D/section-4.36) | Real reg, not naive string equality |
| Net contents | Parse quantity + unit (750mL == 750 mL) | Formatting shouldn't fail a match |
| **Gov't warning** | Exact text (high-threshold fuzzy) + ALL-CAPS check; bold flagged for human | Strictest field |

**A subtle one I called out deliberately:** 4.36's ±1.0%/±1.5% tolerance is a
*production* tolerance (actual alcohol vs labeled alcohol) — a different axis
from label-vs-application. Applying it here would be wrong, so I don't, and I
say why in `match_abv`. Knowing *which* tolerance applies to *which* comparison
is the kind of domain nuance the agents were describing.

Statuses are intentionally three-valued — **pass / review / fail** — not a
binary. "Review" is where the human-in-the-loop lives.

---

## 4. What I deliberately did NOT do

- **No cloud LLM** — violates the network constraint; slower; non-deterministic.
- **No bold detection** — flagged for humans instead of faked.
- **No batch UI / persistence / auth** — out of prototype scope; documented as
  next steps.

Naming the cut lines is the point: it shows the scope was a choice, not an
oversight.

---

## 5. Testing

`tests/test_matching.py` proves the verification logic with **no image and no
model** — it feeds label text straight in. 12 cases cover each field's pass,
mismatch, and edge behavior (brand case-flagging, ABV range, table-wine,
warning all-caps/missing). Fast and deterministic.

---

## 6. 30-second demo script (for a live walkthrough)

1. **Open the app.** "One screen — drop a photo, the form's pre-filled with the
   fixed warning text. Built for agents who aren't technical."
2. **Drop the sample label, hit Verify.** "Result in a couple seconds — and it
   runs entirely locally, no cloud call, because their network blocks that."
3. **Point at the brand row (REVIEW).** "The label says STONE'S THROW, the
   application says Stone's Throw — same letters, different case. It doesn't
   silently pass that; it flags it for a human. That's the nuance Dave raised."
4. **Point at the warning row.** "Text matches and it's all-caps. It can't
   verify *bold* from OCR, so it tells the agent to confirm that visually —
   rather than pretending."
5. **Expand raw OCR.** "Full transparency into what it read, with a confidence
   score per field — so low-confidence fields get human eyes."
6. **Close:** "Clean working core. Batch upload and a local vision-model
   fallback are the documented next steps."
