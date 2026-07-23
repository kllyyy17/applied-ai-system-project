"""
Evaluation harness for VibeMatch.

Runs the guarded recommender (src.reliability.recommend_with_guardrails) over
the cases in eval/cases.yaml and measures how reliably it behaves:

  - Correctness : does the #1 pick have the expected genre/mood? (genre@1, mood@1)
  - Determinism : does the same input give byte-identical output every run?
  - Stability   : how much does the top-5 churn under a small weight nudge?
  - Guardrails  : does the blank-slate guardrail fire, does confidence clear the
                  bar, is filler flagged when expected?

Run it:  python -m eval.evaluate
It prints a summary table and writes eval/report.md. The metric functions are
also imported by tests/test_eval.py, which turns the key numbers into pass/fail
gates.
"""

import os
from typing import Dict, List, Tuple

import yaml

# Import the app's real code paths so we measure the shipping behavior.
try:
    from src.recommender import load_songs, DEFAULT_WEIGHTS
    from src.reliability import recommend_with_guardrails
except ImportError:  # allow `python eval/evaluate.py` from the project root
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from src.recommender import load_songs, DEFAULT_WEIGHTS
    from src.reliability import recommend_with_guardrails

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
CASES_PATH = os.path.join(_HERE, "cases.yaml")
DATA_PATH = os.path.join(_ROOT, "data", "songs.csv")
REPORT_PATH = os.path.join(_HERE, "report.md")

# A fixed (non-random) weight nudge used for the stability probe: lean harder on
# energy, ease off genre. Deterministic so the metric is reproducible.
STABILITY_NUDGE = {"energy": 1.25, "genre": 0.75}

_CONFIDENCE_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3}


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #
def load_cases(path: str = CASES_PATH) -> List[Dict]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def prepare_prefs(case: Dict) -> Dict:
    """Case prefs with the shared DEFAULT_WEIGHTS injected when absent."""
    prefs = dict(case.get("prefs") or {})
    if prefs and "weights" not in prefs:
        prefs["weights"] = DEFAULT_WEIGHTS
    return prefs


def _ids(recs: List[Tuple]) -> List[int]:
    return [song["id"] for song, *_ in recs]


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def check_case(case: Dict, songs: List[Dict]) -> Dict:
    """
    Evaluate one case against its expectations. Returns a result record with the
    observed values plus a per-expectation pass/fail breakdown.
    """
    prefs = prepare_prefs(case)
    expect = case.get("expect", {}) or {}
    recs, verdict = recommend_with_guardrails(prefs, songs, k=5)

    top = recs[0][0] if recs else None
    observed = {
        "top_genre": top["genre"] if top else None,
        "top_mood": top["mood"] if top else None,
        "confidence": verdict["confidence"]["level"],
        "blank_slate": verdict["blank_slate"],
        "n_filler": verdict["n_filler"],
    }

    checks: Dict[str, bool] = {}
    if "top_genre" in expect:
        checks["top_genre"] = observed["top_genre"] == expect["top_genre"]
    if "top_mood" in expect:
        checks["top_mood"] = observed["top_mood"] == expect["top_mood"]
    if "min_confidence" in expect:
        checks["min_confidence"] = (
            _CONFIDENCE_RANK.get(observed["confidence"], 0)
            >= _CONFIDENCE_RANK.get(expect["min_confidence"], 0)
        )
    if "blank_slate" in expect:
        checks["blank_slate"] = observed["blank_slate"] == expect["blank_slate"]
    if "min_filler" in expect:
        checks["min_filler"] = observed["n_filler"] >= expect["min_filler"]

    return {
        "name": case["name"],
        "kind": case.get("kind", "core"),
        "observed": observed,
        "checks": checks,
        "passed": all(checks.values()) if checks else True,
    }


def determinism(case: Dict, songs: List[Dict], runs: int = 3) -> bool:
    """True if `runs` repeated evaluations yield identical id+score sequences."""
    prefs = prepare_prefs(case)

    def signature():
        recs, _ = recommend_with_guardrails(prefs, songs, k=5)
        return [(song["id"], round(score, 6)) for song, score, *_ in recs]

    first = signature()
    return all(signature() == first for _ in range(runs - 1))


def stability_churn(case: Dict, songs: List[Dict]) -> float:
    """
    Fraction of top-5 positions whose song changes when weights are nudged by
    STABILITY_NUDGE. 0.0 = perfectly stable, 1.0 = every position moved.
    Blank-slate cases have no weights to nudge, so they report 0.0.
    """
    prefs = prepare_prefs(case)
    if not prefs.get("weights"):
        return 0.0

    base, _ = recommend_with_guardrails(prefs, songs, k=5)

    nudged = dict(prefs)
    nudged["weights"] = {
        feat: w * STABILITY_NUDGE.get(feat, 1.0)
        for feat, w in prefs["weights"].items()
    }
    pert, _ = recommend_with_guardrails(nudged, songs, k=5)

    base_ids, pert_ids = _ids(base), _ids(pert)
    if not base_ids:
        return 0.0
    changed = sum(1 for a, b in zip(base_ids, pert_ids) if a != b)
    return changed / len(base_ids)


def evaluate(cases_path: str = CASES_PATH, data_path: str = DATA_PATH) -> Dict:
    """Run every metric over every case and return an aggregate results dict."""
    cases = load_cases(cases_path)
    songs = load_songs(data_path)

    case_results = [check_case(c, songs) for c in cases]
    det_results = {c["name"]: determinism(c, songs) for c in cases}
    churn_results = {c["name"]: stability_churn(c, songs) for c in cases}

    core = [r for r in case_results if r["kind"] == "core"]

    def _rate(records, key):
        applicable = [r for r in records if key in r["checks"]]
        if not applicable:
            return None
        return sum(r["checks"][key] for r in applicable) / len(applicable)

    summary = {
        "genre_at_1": _rate(core, "top_genre"),
        "mood_at_1": _rate(core, "top_mood"),
        "determinism_rate": sum(det_results.values()) / len(det_results),
        "guardrail_pass_rate": _rate(case_results, "blank_slate"),
        "cases_passed": sum(r["passed"] for r in case_results),
        "cases_total": len(case_results),
        "mean_core_churn": (
            sum(churn_results[r["name"]] for r in core) / len(core) if core else 0.0
        ),
    }

    return {
        "cases": case_results,
        "determinism": det_results,
        "churn": churn_results,
        "summary": summary,
    }


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #
def render_report(results: Dict) -> str:
    s = results["summary"]

    def pct(x):
        return "n/a" if x is None else f"{x:.0%}"

    lines = [
        "# VibeMatch Evaluation Report",
        "",
        "_Generated by `python -m eval.evaluate`._",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| genre@1 (core) | {pct(s['genre_at_1'])} |",
        f"| mood@1 (core) | {pct(s['mood_at_1'])} |",
        f"| Determinism | {pct(s['determinism_rate'])} |",
        f"| Guardrail correctness | {pct(s['guardrail_pass_rate'])} |",
        f"| Mean core rank churn (weight nudge) | {s['mean_core_churn']:.0%} |",
        f"| Cases passed | {s['cases_passed']}/{s['cases_total']} |",
        "",
        "## Per-case detail",
        "",
        "| Case | Kind | Top pick | Confidence | Filler | Deterministic | Churn | Pass |",
        "|------|------|----------|------------|--------|---------------|-------|------|",
    ]
    for r in results["cases"]:
        o = r["observed"]
        name = r["name"]
        top = f"{o['top_genre']}/{o['top_mood']}" if o["top_genre"] else "-"
        det = "yes" if results["determinism"][name] else "NO"
        churn = f"{results['churn'][name]:.0%}"
        passed = "PASS" if r["passed"] else "FAIL"
        lines.append(
            f"| {name} | {r['kind']} | {top} | {o['confidence']} | "
            f"{o['n_filler']} | {det} | {churn} | {passed} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    results = evaluate()
    report = render_report(results)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report)

    s = results["summary"]
    print(report)
    print(f"\nReport written to {os.path.relpath(REPORT_PATH, _ROOT)}")
    if s["cases_passed"] < s["cases_total"]:
        print("Some cases FAILED - see the table above.")


if __name__ == "__main__":
    main()