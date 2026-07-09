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
    from .recommender import load_songs, recommend_songs
except ImportError:
    from recommender import load_songs, recommend_songs


# A reusable "balanced" weight set so profiles differ by *targets*, not by
# weighting. This keeps comparisons across profiles fair.
BALANCED_WEIGHTS = {
    "genre": 2.0,
    "mood": 1.0,
    "energy": 2.0,
    "valence": 1.0,
    "danceability": 1.0,
    "acousticness": 1.5,
    "tempo": 1.0,
}


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
    """Run the recommender for one profile and print its top 5 with reasons."""
    recommendations = recommend_songs(user_prefs, songs, k=5)

    genre = user_prefs.get("favorite_genre", "any")
    mood = user_prefs.get("favorite_mood", "any")
    print(f"\nProfile: {name}")
    print(f"Top {len(recommendations)} recommendations "
          f"(target genre='{genre}', mood='{mood}')")
    print("=" * 60)

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n{rank}. {song['title']} - {song['artist']}  "
              f"[{song['genre']} / {song['mood']}]")
        print(f"   Score: {score:.2f}")
        print("   Reasons:")
        # explanation is a "; "-joined string of reasons; show one per line.
        for reason in explanation.split("; "):
            print(f"     - {reason}")


def main() -> None:
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