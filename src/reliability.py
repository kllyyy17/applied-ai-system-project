"""
Reliability layer for VibeMatch.

This is NOT a side report — it sits in the recommendation path and changes what
the system returns:

  1. Blank-slate guardrail  - an empty profile no longer gets 5 songs faked at
                              0.00. We detect "I don't know you yet" and return
                              an honest diverse sampler instead.
  2. Confidence scoring     - every real recommendation set carries a confidence
                              (how close the top pick is to a perfect match), so
                              a weak list is labelled weak.
  3. Filler flagging        - picks that match neither the favorite genre nor the
                              favorite mood are marked as cross-genre filler
                              rather than presented as equals.
  4. Logging                - every run is logged (profile, guardrails fired,
                              confidence, filler count) for auditability.

The scoring math itself still lives in recommender.py; this module wraps it.
"""

import logging
from typing import Dict, List, Tuple

# Works both as `python -m src.main` (relative) and `python src/main.py` (absolute).
try:
    from .recommender import recommend_songs
except ImportError:
    from recommender import recommend_songs


logger = logging.getLogger("vibematch.reliability")

# Confidence thresholds on the 0.0-1.0 ratio (top score / best possible score).
CONFIDENCE_HIGH = 0.66
CONFIDENCE_LOW = 0.33

NUMERIC_FEATURES = ("energy", "valence", "danceability", "acousticness", "tempo")


def configure_logging(logfile: str = "vibematch.log",
                      level: int = logging.INFO) -> logging.Logger:
    """
    Set up file logging for the whole `vibematch` logger tree. Safe to call more
    than once - it won't stack duplicate handlers.
    """
    root = logging.getLogger("vibematch")
    root.setLevel(level)
    if not root.handlers:
        handler = logging.FileHandler(logfile, encoding="utf-8")
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        root.addHandler(handler)
    return root


def is_blank_slate(user_prefs: Dict) -> bool:
    """
    True when the profile tells us nothing: no favorite genre, no favorite mood,
    and no numeric targets. These profiles cannot produce a real match.
    """
    if not user_prefs:
        return True
    has_genre = bool(user_prefs.get("favorite_genre"))
    has_mood = bool(user_prefs.get("favorite_mood"))
    has_target = any(
        user_prefs.get(f"target_{feat}") is not None for feat in NUMERIC_FEATURES
    )
    return not (has_genre or has_mood or has_target)


def max_possible_score(user_prefs: Dict) -> float:
    """
    The best score any song could earn for this profile: full categorical bonus
    for each stated preference plus the full weight of each numeric target (a
    perfect closeness of 1.0). Used as the denominator for confidence.
    """
    weights = user_prefs.get("weights", {})
    total = 0.0
    if user_prefs.get("favorite_genre"):
        total += weights.get("genre", 0.0)
    if user_prefs.get("favorite_mood"):
        total += weights.get("mood", 0.0)
    for feat in NUMERIC_FEATURES:
        if user_prefs.get(f"target_{feat}") is not None:
            total += weights.get(feat, 0.0)
    return total


def compute_confidence(user_prefs: Dict,
                       ranked: List[Tuple[Dict, float, str]]) -> Dict:
    """
    How much should we trust the top recommendation? Ratio of the top pick's
    score to the best score achievable for this profile, bucketed into
    high / medium / low.
    """
    if not ranked:
        return {"score": 0.0, "level": "low", "reason": "no songs to rank"}
    ceiling = max_possible_score(user_prefs)
    if ceiling <= 0:
        return {"score": 0.0, "level": "low",
                "reason": "profile specifies no scorable preferences"}
    top_score = ranked[0][1]
    ratio = max(0.0, min(1.0, top_score / ceiling))
    if ratio >= CONFIDENCE_HIGH:
        level = "high"
    elif ratio >= CONFIDENCE_LOW:
        level = "medium"
    else:
        level = "low"
    return {
        "score": ratio,
        "level": level,
        "reason": f"top pick scored {top_score:.2f} of {ceiling:.2f} possible",
    }


def is_filler(user_prefs: Dict, song: Dict) -> bool:
    """
    A pick is filler when it anchors to neither the favorite genre nor the
    favorite mood - i.e. it's on the list only to fill space, not because it
    matches what the user actually asked for.
    """
    genre_match = song.get("genre") == user_prefs.get("favorite_genre")
    mood_match = song.get("mood") == user_prefs.get("favorite_mood")
    return not (genre_match or mood_match)


def diverse_picks(songs: List[Dict], k: int = 5) -> List[Dict]:
    """
    Honest fallback for a blank slate: one song per distinct genre (first seen),
    topping up with whatever remains if there aren't k distinct genres.
    """
    picks: List[Dict] = []
    seen_genres = set()
    for song in songs:
        genre = song.get("genre")
        if genre not in seen_genres:
            seen_genres.add(genre)
            picks.append(song)
        if len(picks) >= k:
            return picks
    for song in songs:
        if song not in picks:
            picks.append(song)
            if len(picks) >= k:
                break
    return picks[:k]


def recommend_with_guardrails(
    user_prefs: Dict, songs: List[Dict], k: int = 5
) -> Tuple[List[Tuple[Dict, float, str, bool]], Dict]:
    """
    The guarded entry point the app should call instead of recommend_songs.

    Returns (recommendations, verdict):
      - recommendations: list of (song, score, explanation, is_filler)
      - verdict: what the guardrails decided (blank_slate, confidence, n_filler,
                 fallback)
    """
    # Blank slate: refuse to fake a match; hand back a labelled diverse sampler.
    if is_blank_slate(user_prefs):
        picks = diverse_picks(songs, k)
        recs = [
            (song, 0.0, "diverse fallback pick (no profile provided)", False)
            for song in picks
        ]
        verdict = {
            "blank_slate": True,
            "confidence": {"score": 0.0, "level": "none",
                           "reason": "empty profile - diverse sampler, not a match"},
            "n_filler": 0,
            "fallback": "diverse",
        }
        _log_run(user_prefs, verdict)
        return recs, verdict

    # Normal path. Guard the scoring call so a bad row can't crash the app.
    try:
        ranked = recommend_songs(user_prefs, songs, k=k)
    except Exception:  # pragma: no cover - defensive guardrail
        logger.exception("recommend_songs failed; returning empty result")
        verdict = {
            "blank_slate": False,
            "confidence": {"score": 0.0, "level": "low", "reason": "scoring error"},
            "n_filler": 0,
            "fallback": "error",
        }
        return [], verdict

    recs = [
        (song, score, explanation, is_filler(user_prefs, song))
        for song, score, explanation in ranked
    ]
    verdict = {
        "blank_slate": False,
        "confidence": compute_confidence(user_prefs, ranked),
        "n_filler": sum(1 for rec in recs if rec[3]),
        "fallback": None,
    }
    _log_run(user_prefs, verdict)
    return recs, verdict


def _log_run(user_prefs: Dict, verdict: Dict) -> None:
    """Emit one structured log line per recommendation run."""
    conf = verdict["confidence"]
    logger.info(
        "recommend genre=%s mood=%s blank_slate=%s confidence=%s(%.2f) filler=%d fallback=%s",
        user_prefs.get("favorite_genre", "-"),
        user_prefs.get("favorite_mood", "-"),
        verdict["blank_slate"],
        conf["level"],
        conf["score"],
        verdict["n_filler"],
        verdict["fallback"],
    )