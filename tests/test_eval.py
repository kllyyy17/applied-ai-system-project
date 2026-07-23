"""
Regression gates built on the evaluation harness (eval/evaluate.py).

These turn the reliability metrics into pass/fail tests, so `pytest` fails if a
future change breaks correctness, determinism, or the guardrails.
"""

import pytest

from eval.evaluate import evaluate, determinism, load_cases, load_songs, CASES_PATH, DATA_PATH


@pytest.fixture(scope="module")
def results():
    return evaluate()


def test_top1_genre_accuracy(results):
    # Every core profile's #1 pick must be in the requested genre.
    assert results["summary"]["genre_at_1"] == 1.0


def test_top1_mood_accuracy(results):
    assert results["summary"]["mood_at_1"] == 1.0


def test_all_runs_are_deterministic(results):
    # Same input -> identical output, for every case.
    assert results["summary"]["determinism_rate"] == 1.0


def test_guardrails_behave_as_expected(results):
    assert results["summary"]["guardrail_pass_rate"] == 1.0


def test_blank_slate_guardrail_fires(results):
    blank = next(r for r in results["cases"] if r["name"] == "The Blank Slate")
    assert blank["observed"]["blank_slate"] is True
    assert blank["passed"]


def test_core_ranking_is_stable_under_small_weight_nudge(results):
    # A mild weight change must not scramble core recommendations.
    assert results["summary"]["mean_core_churn"] <= 0.4


def test_every_case_passes(results):
    s = results["summary"]
    assert s["cases_passed"] == s["cases_total"]


def test_determinism_helper_directly():
    # Guard the determinism check itself against a single-case regression.
    songs = load_songs(DATA_PATH)
    for case in load_cases(CASES_PATH):
        assert determinism(case, songs), f"{case['name']} was non-deterministic"