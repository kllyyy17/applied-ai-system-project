"""
Command line runner for the Music Recommender Simulation.

This file runs the recommender against a battery of user taste profiles so we
can evaluate its behavior. There are two groups:

  1. CORE profiles      - realistic listeners the system should handle well.
  2. ADVERSARIAL profiles - edge cases designed to "trick" the scoring logic
                            (conflicting preferences, impossible targets, and
                            empty input) so we can see where it breaks down.

The scoring itself lives in recommender.py:
  - load_songs
  - score_song
  - recommend_songs
"""

# Works both as `python -m src.main` (relative) and `python src/main.py` (absolute).
try:
    from .recommender import load_songs, DEFAULT_WEIGHTS
    from .reliability import recommend_with_guardrails, configure_logging
except ImportError:
    from recommender import load_songs, DEFAULT_WEIGHTS
    from reliability import recommend_with_guardrails, configure_logging


# A reusable "balanced" weight set so profiles differ by *targets*, not by
# weighting. This keeps comparisons across profiles fair. Aliased to the
# shared DEFAULT_WEIGHTS in recommender.py so the two never drift apart.
BALANCED_WEIGHTS = DEFAULT_WEIGHTS


# ---------------------------------------------------------------------------
# CORE PROFILES - realistic listeners
# ---------------------------------------------------------------------------

# 1) High-Energy Pop: upbeat, danceable, radio-friendly, fast tempo.
HIGH_ENERGY_POP = {
    "favorite_genre": "pop",
    "favorite_mood": "happy",
    "target_energy": 0.90,
    "target_valence": 0.85,
    "target_danceability": 0.85,
    "target_acousticness": 0.10,
    "target_tempo": 0.57,   # ~130 bpm
    "weights": BALANCED_WEIGHTS,
}

# 2) Chill Lofi: calm, organic, study/relax vibe (the original default profile).
CHILL_LOFI = {
    "favorite_genre": "lofi",
    "favorite_mood": "chill",
    "target_energy": 0.35,
    "target_valence": 0.60,
    "target_danceability": 0.55,
    "target_acousticness": 0.80,
    "target_tempo": 0.20,   # ~78 bpm
    "weights": BALANCED_WEIGHTS,
}

# 3) Deep Intense Rock: hard-hitting, fast, electric, emotionally heavy.
DEEP_INTENSE_ROCK = {
    "favorite_genre": "rock",
    "favorite_mood": "intense",
    "target_energy": 0.92,
    "target_valence": 0.40,
    "target_danceability": 0.60,
    "target_acousticness": 0.12,
    "target_tempo": 0.73,   # ~152 bpm
    "weights": BALANCED_WEIGHTS,
}


# ---------------------------------------------------------------------------
# ADVERSARIAL / EDGE-CASE PROFILES
# Suggested during the "System Evaluation" session to stress-test the scoring.
# ---------------------------------------------------------------------------

# 4) The Contradiction: "I want SAD music, but make it HIGH ENERGY."
#    Mood/valence say somber and gloomy; energy/tempo say adrenaline. The two
#    signals fight, so no single song can satisfy both. What wins?
CONTRADICTION = {
    "favorite_genre": "blues",
    "favorite_mood": "somber",
    "target_energy": 0.95,      # cranked
    "target_valence": 0.10,     # very sad
    "target_danceability": 0.50,
    "target_acousticness": 0.50,
    "target_tempo": 0.85,       # very fast (~169 bpm)
    "weights": BALANCED_WEIGHTS,
}

# 5) The Blank Slate: an empty profile with no preferences at all.
#    No genre, no mood, no targets, no weights -> every song scores 0.0.
#    Tests tie-breaking: what does the system return when it knows nothing?
BLANK_SLATE = {}


# (name, profile) pairs, grouped for readable output.
CORE_PROFILES = [
    ("High-Energy Pop", HIGH_ENERGY_POP),
    ("Chill Lofi", CHILL_LOFI),
    ("Deep Intense Rock", DEEP_INTENSE_ROCK),
]

ADVERSARIAL_PROFILES = [
    ("The Contradiction (sad + high-energy)", CONTRADICTION),
    ("The Blank Slate (no preferences)", BLANK_SLATE),
]


def print_recommendations(name: str, user_prefs: dict, songs: list) -> None:
    """
    Run the guarded recommender for one profile and print its top 5.

    Output is shaped by the reliability layer: a blank slate prints an honest
    "I don't know you yet" sampler, real profiles print a confidence banner, and
    cross-genre filler picks are labelled instead of shown as equals.
    """
    recommendations, verdict = recommend_with_guardrails(user_prefs, songs, k=5)

    genre = user_prefs.get("favorite_genre", "any")
    mood = user_prefs.get("favorite_mood", "any")
    conf = verdict["confidence"]
    print(f"\nProfile: {name}")

    if verdict["blank_slate"]:
        print("  [guardrail] No preferences given - I don't know your taste yet.")
        print("  Showing a diverse sampler instead of a fake match:")
    else:
        print(f"Top {len(recommendations)} recommendations "
              f"(target genre='{genre}', mood='{mood}')")
        print(f"  Confidence: {conf['level'].upper()} ({conf['score']:.0%}) "
              f"- {conf['reason']}")
        if verdict["n_filler"]:
            print(f"  Note: {verdict['n_filler']} of {len(recommendations)} picks "
                  f"are cross-genre filler (no genre/mood match).")
    print("=" * 60)

    for rank, (song, score, explanation, filler) in enumerate(recommendations, start=1):
        tag = "  [filler]" if filler else ""
        print(f"\n{rank}. {song['title']} - {song['artist']}  "
              f"[{song['genre']} / {song['mood']}]{tag}")
        print(f"   Score: {score:.2f}")
        print("   Reasons:")
        # explanation is a "; "-joined string of reasons; show one per line.
        for reason in explanation.split("; "):
            print(f"     - {reason}")


def main() -> None:
    configure_logging()
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")

    print("\n" + "#" * 60)
    print("# CORE PROFILES")
    print("#" * 60)
    for name, prefs in CORE_PROFILES:
        print_recommendations(name, prefs, songs)

    print("\n\n" + "#" * 60)
    print("# ADVERSARIAL / EDGE-CASE PROFILES")
    print("#" * 60)
    for name, prefs in ADVERSARIAL_PROFILES:
        print_recommendations(name, prefs, songs)


if __name__ == "__main__":
    main()