# Labelify — Approach & Decisions

A quick rundown of how I read the brief and what I built. Two rules I stuck to:
build a clean working core instead of a pile of half-finished features (the brief
asked for that), and tie every choice back to something a stakeholder actually
said.

---

## 1. How I looked at the problem

The brief says "AI-powered," but the real job is simpler than throwing it at a
chatbot:

> Read the text off a photo of a label, then check each required field against
> what the producer put on the application.

That breaks into two parts that don't depend on each other:

- **Reading the label** (photo → text). This is the hard part, and it's the AI.
- **Checking the fields** (text → pass / review / fail). This is plain logic.

Keeping them apart was the main call. The checking logic can be tested without
any images, each piece can be swapped out on its own, and I can always say
exactly why a field passed or failed — which matters when an agent has to stand
behind the result.

**Where's the AI?** It's the OCR. RapidOCR is a set of trained neural nets that
find and read the text in a photo. Reading a wine label shot at an angle, with
glare, isn't something you can hand-code — that's the machine-learning part. I
kept the field-checking after that as plain rules *on purpose*: for a legal
check you want something you can point at and explain, not a black box.

---

## 2. Choices, tied to what each person asked for

| What they said | What I did | Why |
| --- | --- | --- |
| "Network blocks outside traffic… avoid cloud APIs" — **Marcus (IT)** | No cloud AI. The OCR runs right on the server (RapidOCR). | A cloud call would just fail on their network. This is the big one, and it rules out the easy "call GPT-4 Vision" answer. |
| "Results back in ~5 seconds or nobody uses it" — **Sarah** | Reading the photo is the only slow step (~2–3s). I start it the moment a photo is added, so it's done before they click Verify. See section 4. | Move the slow part off the wait instead of making it faster. |
| "My mother could figure it out" — **Sarah** | One page. Three labeled photo slots (Front / Back / Neck). Fill in the application fields. Results are a green-check / red-X list. | It looks like the paper checklist they already use. Nothing new to learn. |
| "STONE'S THROW vs Stone's Throw" — **Dave** | Brand check flags a case or punctuation difference as **review**, never a silent pass. | That difference is the whole point. Auto-fixing it would throw away the thing Dave cares about. |
| Warning = exact text, all caps, bold — **Jenny** | The app checks the warning itself against the fixed federal wording — it's not a field the agent types, because it's the same on every product (27 CFR Part 16). Bold can't be read from a photo, so it's flagged for a person. | A legally-fixed string shouldn't be retyped per product; that just invites typos. And I won't fake a check I can't actually do. |
| Photos at angles / glare — **Jenny** | OCR handles rotation; the matching shrugs off small misreads; every field shows what was read and a confidence score. | Shaky reads go to a human instead of passing by accident. The tool helps the agent, it doesn't replace them. |
| Batch upload for importers — **Sarah** | **Built.** Upload a CSV of products plus all the images and get a results table. | It's the single check run in a loop. |

---

## 3. One rule per field

Checking every field the same way is the trap. Each one needs its own rule:

| Field | Rule | Why |
| --- | --- | --- |
| Brand name | Fuzzy match; a case or punctuation difference → **review** | Dave's point |
| Class / type | The COLA gives a category code ("TABLE RED WINE") but the label shows the grape ("Cabernet Sauvignon"), so a small lookup maps the code to the names that count | The code is never printed on the bottle |
| ABV | Compare the number, not the text; also allow a stated range and "table/light wine" per [27 CFR 4.36](https://www.ecfr.gov/current/title-27/chapter-I/subchapter-A/part-4/subpart-D/section-4.36) | Real rule, not just string-equals |
| Net contents | Match number + unit, spacing and all (750mL == 750 mL) | Formatting shouldn't fail a real match |
| Producer / Origin | Fuzzy "is it on the label" | Survives OCR noise |
| Gov't warning | Check the words are all there and in caps — ignoring spaces and punctuation, since OCR mangles the dense all-caps print; flag bold for a person | Strictest field, but don't fail it over OCR spacing |

Two things worth calling out:

- **The ABV tolerance trap.** 4.36's ±1.0% / ±1.5% tolerance is about *actual*
  alcohol vs *labeled* alcohol — a different thing from label-vs-application. So
  I don't apply it here, and I say why in `match_abv`. Knowing which tolerance
  goes with which check is exactly the kind of detail the agents were describing.
- **The warning and OCR spacing.** OCR often drops the spaces between the
  warning's all-caps words ("SURGEONGENERAL,WOMENSHOULDNOT…"). The words are all
  there and in order — it's a reading glitch, not wrong text. So I compare on the
  letters only, and a correct-but-jammed-together warning passes to review
  instead of getting failed.

Results are three states — **pass / review / fail** — not just yes/no. "Review"
is where a person takes a look.

---

## 4. Hitting the 5-second goal

Reading a photo is the slow step (~2–3s each on the free server). Instead of
trying to make that faster, I moved it off the clock:

- The moment a photo is dropped into a slot, the app sends it off to be read in
  the background — while the agent is still typing the application data.
- The slot shows "reading… → ✓ ready" so they can see it's working.
- By the time they hit Verify, the reading is already done, so the check itself
  is basically instant. The screen shows the time, e.g. "⏱ 0.0s (OCR
  pre-loaded)."

Same total work — it just doesn't happen while the agent is staring at a button.
If they hit Verify before a photo's done, it just waits for that one.

---

## 5. What happens to the images (no storage)

Uploaded images are never saved. They're read into memory, run through OCR, and
thrown away when the request finishes. Nothing is written to disk, nothing is
cached, no database. That keeps it simple and matches Marcus's "no PII storage"
line — there's nothing sitting around to leak or clean up.

---

## 6. What I left out on purpose

- **No cloud AI** — would break on their network, and it's slower anyway.
- **No bold check** — OCR reads words, not how bold they are, so I flag bold for
  a person instead of faking it. The real fix is reading the producer's source
  print file (bold is in the font info), but the public registry only has
  photos, so there's nothing to test that against.
- **No login / database** — not needed for a prototype, and storing nothing is
  the safer default.

Calling out the cut lines is the point: the scope was a choice, not something I
missed.

---

## 7. Testing

`tests/test_matching.py` proves the checking logic with **no images and no OCR
model** — it feeds label text straight in. 26 small tests cover each field's
pass / mismatch / edge cases (brand case-flag, ABV ranges, the class lookup,
the warning's all-caps-and-spacing quirks) plus the batch manifest parsing.
Fast and easy to run.

There's also a real-world check in [EVALUATION.md](EVALUATION.md): 40 actual
labels pulled from the registry, run through the live app, with the results and
what they mean. The exact 40 are bundled in `tests/eval_labels/` so anyone can
reproduce it.

---

## 8. 30-second demo (for a live walkthrough)

1. **Open the app.** "One screen. Drop the front and back photos, fill in the
   application fields. The warning isn't a field — the app already knows it."
2. **Add the photos.** "Watch the slots say reading then ready — it's reading
   them in the background while I type, so the check itself is instant."
3. **Hit Verify.** "Done in a fraction of a second, and it all runs locally — no
   cloud, because their network blocks that."
4. **Point at the brand row (review).** "Label says STONE'S THROW, application
   says Stone's Throw. Same letters, different case — it doesn't quietly pass
   that, it flags it. That's Dave's nuance."
5. **Point at the warning row.** "Words are all there and in caps, so it passes
   to review. It can't tell if it's bold from a photo, so it asks a person to
   check that — instead of pretending."
6. **Switch to the Batch tab.** "Same thing for importers — a CSV of products
   plus the images, and you get the whole table at once."
7. **Close:** "Clean working core, all the stakeholder asks covered, and the
   next steps are written down."
