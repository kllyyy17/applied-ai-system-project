"""
Command line runner for the Music Recommender Simulation.

This file helps you quickly run and test your recommender.

You will implement the functions in recommender.py:
- load_songs
- score_song
- recommend_songs
"""

# Works both as `python -m src.main` (relative) and `python src/main.py` (absolute).
try:
    from .recommender import load_songs, recommend_songs
except ImportError:
    from recommender import load_songs, recommend_songs


def main() -> None:
    songs = load_songs("data/songs.csv")
    print(f"Loaded songs: {len(songs)}")

    # Taste profile: a "lofi study / chill" listener.
    # Categorical targets are matched for a bonus; numeric targets are on a 0.0-1.0
    # scale and scored by closeness of fit. `weights` control how much each feature counts.
    user_prefs = {
        "favorite_genre": "lofi",
        "favorite_mood": "chill",
        "target_energy": 0.35,          # calm, not hyped
        "target_valence": 0.60,         # gently positive, not euphoric
        "target_danceability": 0.55,    # some groove, but not a dance track
        "target_acousticness": 0.80,    # prefers organic/acoustic texture
        "target_tempo": 0.20,           # normalized ~78 bpm (slow)
        "weights": {
            "genre": 2.0,
            "mood": 1.0,
            "energy": 2.0,
            "valence": 1.0,
            "danceability": 1.0,
            "acousticness": 1.5,
            "tempo": 1.0,
        },
    }

    recommendations = recommend_songs(user_prefs, songs, k=5)

    genre = user_prefs["favorite_genre"]
    mood = user_prefs["favorite_mood"]
    print(f"\nTop {len(recommendations)} recommendations "
          f"for a '{genre} / {mood}' listener")
    print("=" * 56)

    for rank, (song, score, explanation) in enumerate(recommendations, start=1):
        print(f"\n{rank}. {song['title']} - {song['artist']}  "
              f"[{song['genre']} / {song['mood']}]")
        print(f"   Score: {score:.2f}")
        print("   Reasons:")
        # explanation is a "; "-joined string of reasons; show one per line.
        for reason in explanation.split("; "):
            print(f"     - {reason}")


if __name__ == "__main__":
    main()
