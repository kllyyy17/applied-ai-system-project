# VibeMatch — System Architecture

This diagram shows how VibeMatch is organized: the components, how data flows
from input to output, and where **testing and human review** check the AI's
results. The advanced feature is a **Reliability / Testing system**, so the
diagram highlights both the guardrails that run inline (changing what the app
returns) and the offline evaluation harness that measures and gates that
behavior.

```mermaid
flowchart TB
    %% ---------------- INPUTS ----------------
    subgraph IN["1 · Inputs"]
        CSV[("data/songs.csv<br/>20-song catalog")]
        PROFILE["User taste profile<br/>(genre, mood, feature targets, weights)"]
    end

    LOAD["load_songs()<br/><i>recommender.py</i>"]
    CSV --> LOAD

    %% ---------------- RELIABILITY LAYER (orchestrator) ----------------
    subgraph REL["2 · Reliability Layer — recommend_with_guardrails() · reliability.py"]
        BLANK{"is_blank_slate?<br/>(no genre/mood/targets)"}
        DIVERSE["diverse_picks()<br/>honest fallback sampler"]
        CONF["compute_confidence()<br/>top score ÷ best possible"]
        FILLER["is_filler()<br/>flag cross-genre padding"]
        LOG[["_log_run()<br/>→ vibematch.log"]]
    end

    %% ---------------- CORE ENGINE ----------------
    subgraph CORE["3 · Core Scoring Engine — recommender.py"]
        SCORE["score_song()<br/>categorical bonus + closeness of fit"]
        RANK["recommend_songs()<br/>score all → sort → top-k"]
        SCORE --> RANK
    end

    LOAD --> BLANK
    PROFILE --> BLANK
    BLANK -- "yes: don't fake a match" --> DIVERSE
    BLANK -- "no" --> RANK
    RANK --> CONF --> FILLER
    DIVERSE --> LOG
    FILLER --> LOG

    %% ---------------- OUTPUT ----------------
    subgraph OUT["4 · Output — main.py"]
        RESULT["Ranked top-5 + reasons<br/>+ confidence banner<br/>+ [filler] tags<br/>OR blank-slate sampler"]
    end
    LOG --> RESULT

    %% ---------------- EVALUATION & TESTING (human-in-the-loop) ----------------
    subgraph EVAL["5 · Evaluation & Testing — where results are checked"]
        CASES[("eval/cases.yaml<br/>human-authored expectations")]
        HARNESS["evaluate.py<br/>metrics: genre@1, mood@1,<br/>determinism, stability, guardrails"]
        REPORT[("eval/report.md<br/>metrics table")]
        PYTEST["pytest gates<br/>test_eval.py · test_recommender.py"]
        HUMAN(["👤 Human review<br/>reads report + model_card,<br/>authors cases, sets thresholds"])

        CASES --> HARNESS --> REPORT --> HUMAN
        HARNESS --> PYTEST
        HUMAN -. "refine cases / weights / thresholds" .-> CASES
    end

    %% The harness exercises the SAME guarded path the app uses.
    HARNESS -. "runs the real path" .-> REL
    PYTEST -. "fails build on regression" .-> REL
    RESULT -. "sampled for evaluation" .-> HARNESS

    classDef input fill:#e3f2fd,stroke:#1565c0,color:#0d47a1;
    classDef core fill:#e8f5e9,stroke:#2e7d32,color:#1b5e20;
    classDef rel fill:#fff3e0,stroke:#ef6c00,color:#e65100;
    classDef out fill:#f3e5f5,stroke:#6a1b9a,color:#4a148c;
    classDef test fill:#fce4ec,stroke:#c2185b,color:#880e4f;
    classDef human fill:#fffde7,stroke:#f9a825,color:#f57f17;

    class CSV,PROFILE,LOAD input;
    class SCORE,RANK core;
    class BLANK,DIVERSE,CONF,FILLER,LOG rel;
    class RESULT out;
    class CASES,HARNESS,REPORT,PYTEST test;
    class HUMAN human;
```

## How to read it

1. **Inputs** — a hand-labeled song catalog (`songs.csv`) and a user taste
   profile flow in.
2. **Reliability layer** (`recommend_with_guardrails`) is the entry point. It
   first asks *"do we know this user?"* An empty profile is routed to an honest
   diverse sampler instead of a fake ranking; a real profile is scored.
3. **Core scoring engine** ranks songs by categorical match + closeness of fit.
4. Back in the reliability layer, the result gets a **confidence** score,
   **filler** flags, and a **log line** — then the **output** shows the ranked
   list with its reliability banner.
5. **Evaluation & testing** is where results are checked. `evaluate.py` runs the
   *same guarded path* over human-authored expectations in `cases.yaml`,
   produces `report.md`, and feeds `pytest` gates that fail the build on
   regression. A **human** reads the report and model card, authors the cases,
   and sets the thresholds — closing the loop back onto the inputs and weights.

**Human / testing checkpoints** are the pink and yellow nodes in section 5:
humans author the expected outcomes and thresholds, and the automated harness +
pytest gates verify the AI's output against them on every run.