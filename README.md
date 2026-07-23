# 🎵 VibeMatch — A Music Recommender with a Reliability Layer

## Original Project

This project extends my **Module 3 project: the Music Recommender Simulation
("VibeMatch 1.0")**. The original goal was to build a small, content-based music
recommender that represents songs and a user "taste profile" as data, scores
each song against that profile, and returns the top 5 with a plain-English
reason for every pick. Its core capability was the scoring math — a weighted
blend of categorical matches (genre, mood) and numeric closeness-of-fit (energy,
valence, danceability, acousticness, tempo) — evaluated across a 20-song catalog.

---

## Title and Summary

**VibeMatch 2.0** takes the original rule-based recommender and wraps it in a
**reliability / testing system** so the app no longer just produces rankings —
it *knows how much to trust them*. Every recommendation now carries a confidence
score, cross-genre "filler" picks are labelled instead of disguised as real
matches, and an empty profile triggers an honest "I don't know you yet" fallback
instead of five fake results. An offline evaluation harness measures this
behavior (correctness, determinism, stability, guardrail coverage) and gates it
with automated tests.

**Why it matters:** a recommender that looks confident while knowing nothing is
worse than one that admits uncertainty. This project is a small, readable
demonstration of the difference between *shipping a model* and *shipping a
system you can trust and regression-test* — the reliability engineering that
sits around the AI, not just the AI itself.

---

## Architecture Overview

The full system diagram lives in
[diagrams/architecture.md](diagrams/architecture.md) (editable Mermaid source).

Data flows through five stages:

1. **Inputs** — a hand-labeled catalog (`data/songs.csv`) and a user taste
   profile.
2. **Reliability layer** (`src/reliability.py`) is the single entry point,
   `recommend_with_guardrails()`. It first asks *"do we know this user?"* An
   empty profile is routed to an honest diverse sampler; a real profile is
   scored.
3. **Core scoring engine** (`src/recommender.py`) ranks songs by categorical
   match + closeness of fit — the original VibeMatch 1.0 logic.
4. **Output** (`src/main.py`) prints the ranked top-5 with a confidence banner
   and `[filler]` tags, and every run is logged to `vibematch.log`.
5. **Evaluation & testing** (`eval/`) runs the *same guarded path* over
   human-authored expectations (`eval/cases.yaml`), writes a metrics report, and
   feeds `pytest` gates that fail the build on regression. **A human** authors
   the expected outcomes and thresholds and reviews the report — that is the
   human-in-the-loop checkpoint.

The key design point: the evaluator exercises the *production* recommendation
path, not a separate copy, so the tests measure real behavior.

---

## Setup Instructions

**Requirements:** Python 3.10+.

1. (Optional but recommended) create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate      # macOS / Linux
   .venv\Scripts\activate         # Windows
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the app (prints recommendations for five built-in profiles):

   ```bash
   python -m src.main
   ```

4. Run the evaluation harness (prints a metrics table, writes `eval/report.md`):

   ```bash
   python -m eval.evaluate
   ```

5. Run the tests (correctness + reliability regression gates):

   ```bash
   pytest
   ```

---

## Sample Interactions

Three profiles that show the system in three different states. (Output is
abbreviated; run `python -m src.main` for the full listings.)

### 1. A clear, mainstream taste → high confidence

**Input:** `favorite_genre="lofi", favorite_mood="chill"`, calm/acoustic targets.

```
Profile: Chill Lofi
Top 5 recommendations (target genre='lofi', mood='chill')
  Confidence: HIGH (98%) - top pick scored 9.34 of 9.50 possible
  Note: 1 of 5 picks are cross-genre filler (no genre/mood match).
============================================================

1. Library Rain - Paper Lanterns  [lofi / chill]
   Score: 9.34
   Reasons:
     - genre match: lofi (+2.0)
     - mood match: chill (+1.0)
     - energy fit 100% (+2.00)
     - ...
5. Coffee Shop Stories - Slow Stereo  [jazz / relaxed]  [filler]
   Score: 6.12
```

The top pick is a near-perfect match, so confidence is HIGH. The one non-lofi,
non-chill pick at #5 is honestly labelled `[filler]`.

### 2. A contradictory (adversarial) profile → filler flagging earns its keep

**Input:** `favorite_genre="blues", favorite_mood="somber"` **but**
`target_energy=0.95, target_tempo=0.85` — the user asks for sad music that is
also high-energy. The signals fight.

```
Profile: The Contradiction (sad + high-energy)
Top 5 recommendations (target genre='blues', mood='somber')
  Confidence: HIGH (75%) - top pick scored 7.17 of 9.50 possible
  Note: 4 of 5 picks are cross-genre filler (no genre/mood match).
============================================================

1. Gritline - South Bend Blues Co  [blues / somber]      Score: 7.17
2. Iron Verdict - Ashgrave  [metal / angry]   [filler]   Score: 5.56
3. Storm Runner - Voltline  [rock / intense]  [filler]   Score: 5.16
```

The one true blues/somber match wins, but **4 of 5 picks are filler** — the
high-energy request drags in angry metal and intense rock. The confidence looks
high (the #1 pick is decent) while the filler note reveals the rest of the list
is padding. This is exactly the honesty the reliability layer adds.

### 3. An empty profile → the blank-slate guardrail

**Input:** `{}` — no preferences at all.

```
Profile: The Blank Slate (no preferences)
  [guardrail] No preferences given - I don't know your taste yet.
  Showing a diverse sampler instead of a fake match:
============================================================

1. Sunrise City - Neon Echo        [pop / happy]       Score: 0.00
2. Midnight Coding - LoRoom         [lofi / chill]      Score: 0.00
3. Storm Runner - Voltline          [rock / intense]    Score: 0.00
4. Spacewalk Thoughts - Orbit Bloom [ambient / chill]   Score: 0.00
5. Coffee Shop Stories - Slow Stereo[jazz / relaxed]    Score: 0.00
```

Before the reliability layer, an empty profile returned five songs tied at 0.00
in file order — a fake recommendation dressed up as a real one. Now the system
says it doesn't know you and returns **one song per distinct genre** as an
honest sampler.

---

## Design Decisions

- **Reliability as a wrapper, not a rewrite.** The guardrails live in
  `reliability.py` and *wrap* the original scoring core rather than replacing it.
  This keeps the AI logic and the trust logic separate and readable, and means
  the evaluation harness can test the exact code the app runs.
  *Trade-off:* one extra layer of indirection (`recommend_with_guardrails` calls
  `recommend_songs`) in exchange for testability and a clean separation.
- **Confidence = top score ÷ best-possible score.** A simple, explainable ratio
  instead of a probabilistic model. *Trade-off:* it measures *fit to the stated
  profile*, not real-world accuracy — but with no user history to learn from, an
  honest, interpretable proxy beats a false sense of statistical rigor.
- **Filler = "matches neither favorite genre nor mood."** A deliberately blunt
  rule. *Trade-off:* it can occasionally flag a genuinely good cross-genre pick,
  but over-flagging padding is safer than hiding it.
- **Blank-slate returns a diverse sampler, not nothing.** Refusing outright would
  be unhelpful; faking a ranking would be dishonest. One-song-per-genre is the
  middle path. *Trade-off:* the sampler isn't personalized, and it says so.
- **YAML cases + pytest gates.** Expectations live in human-readable
  `eval/cases.yaml`, separate from the harness code, so a non-programmer can
  read and edit what "correct" means. *Trade-off:* adds a `pyyaml` dependency.
- **Deterministic everything.** No randomness anywhere, so runs are reproducible
  and the determinism metric is meaningful.

---

## Testing Summary

Run with `pytest` (10 tests) and `python -m eval.evaluate` (metrics report).

**What worked:**

| Metric | Result |
|--------|--------|
| genre@1 (core profiles) | 100% |
| mood@1 (core profiles) | 100% |
| Determinism (identical output across runs) | 100% |
| Guardrail correctness (blank-slate fires, confidence clears bar) | 100% |
| Cases passed | 5 / 5 |

- The guardrails behave as designed across all five profiles, including the two
  adversarial ones.
- The **stability probe** (re-ranking under a small weight nudge: energy ×1.25,
  genre ×0.75) surfaced a real insight automatically: the three core profiles
  show **0% rank churn** (rock-stable), but **The Contradiction shows 20% churn**
  — the single most sensitive case. This reproduces, as an automated metric, the
  weight-sensitivity finding from the original project's manual experiment.

**What didn't / limitations found by testing:**

- Confidence can read HIGH (75%) while 4 of 5 picks are filler (the Contradiction
  case). A single top-pick score doesn't capture whole-list quality — a future
  version should fold filler ratio into the confidence signal.
- With one song per genre for 15 of 17 genres, niche profiles are inherently
  hard to serve well; the tests confirm the *behavior* is correct but can't fix
  the thin data.

**What I learned:** writing the harness first forced me to define what "correct"
even means for a recommender (top-1 genre/mood, determinism, stability), and
several of those definitions were not obvious until I tried to assert them.

---

## Reflection

Building the reliability layer taught me that most of the engineering in a
trustworthy AI system lives *around* the model, not inside it — detecting when
the system doesn't know enough, labelling low-quality output, and making
behavior reproducible and testable mattered more than the scoring math itself.

> The graded responsible-AI reflection — how I collaborated with AI, one helpful
> and one flawed AI suggestion, and the system's limitations and bias — is in
> the **[model card](model_card.md)**.