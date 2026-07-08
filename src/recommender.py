import csv
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class Song:
    """
    Represents a song and its attributes.
    Required by tests/test_recommender.py
    """
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float

@dataclass
class UserProfile:
    """
    Represents a user's taste preferences.
    Required by tests/test_recommender.py
    """
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool

class Recommender:
    """
    OOP implementation of the recommendation logic.
    Required by tests/test_recommender.py
    """
    def __init__(self, songs: List[Song]):
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        # TODO: Implement recommendation logic
        return self.songs[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        # TODO: Implement explanation logic
        return "Explanation placeholder"

def load_songs(csv_path: str) -> List[Dict]:
    """
    Loads songs from a CSV file and returns a list of dictionaries.

    Each row becomes one dict. String columns (title, artist, genre, mood)
    are kept as text, while numeric columns are converted so we can do math
    with them later:
      - id, tempo_bpm  -> int
      - energy, valence, danceability, acousticness -> float
    """
    int_fields = {"id", "tempo_bpm"}
    float_fields = {"energy", "valence", "danceability", "acousticness"}

    songs: List[Dict] = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            song: Dict = {}
            for key, value in row.items():
                if key in int_fields:
                    song[key] = int(value)
                elif key in float_fields:
                    song[key] = float(value)
                else:
                    song[key] = value
            songs.append(song)

    return songs

# Tempo is stored as BPM but preferences use a normalized 0.0-1.0 scale.
# This range maps ~78 bpm -> 0.20 (matching main.py's target_tempo comment).
TEMPO_MIN_BPM = 50.0
TEMPO_MAX_BPM = 190.0


def _normalize_tempo(bpm: float) -> float:
    """Map a BPM value into the 0.0-1.0 scale, clamped to that range."""
    norm = (bpm - TEMPO_MIN_BPM) / (TEMPO_MAX_BPM - TEMPO_MIN_BPM)
    return max(0.0, min(1.0, norm))


def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, List[str]]:
    """
    Scores a single song against user preferences.

    Algorithm Recipe:
      - Categorical match (genre, mood): award the feature's full weight as a
        flat bonus when the song matches the user's favorite.
      - Numeric features (energy, valence, danceability, acousticness, tempo):
        all live on a 0.0-1.0 scale, so score by closeness of fit. A perfect
        match earns the full weight; the further apart, the fewer points:
            points = (1 - |target - actual|) * weight

    Returns (score, reasons) where `reasons` is a human-readable list explaining
    where the points came from, e.g. "genre match (+2.0)".
    """
    weights = user_prefs.get("weights", {})
    score = 0.0
    reasons: List[str] = []

    # --- Categorical matches (flat bonus) ---
    if song["genre"] == user_prefs.get("favorite_genre"):
        w = weights.get("genre", 0.0)
        score += w
        reasons.append(f"genre match: {song['genre']} (+{w:.1f})")

    if song["mood"] == user_prefs.get("favorite_mood"):
        w = weights.get("mood", 0.0)
        score += w
        reasons.append(f"mood match: {song['mood']} (+{w:.1f})")

    # --- Numeric features (closeness of fit) ---
    numeric_features = [
        ("energy", song["energy"]),
        ("valence", song["valence"]),
        ("danceability", song["danceability"]),
        ("acousticness", song["acousticness"]),
        ("tempo", _normalize_tempo(song["tempo_bpm"])),
    ]
    for feature, actual in numeric_features:
        target = user_prefs.get(f"target_{feature}")
        if target is None:
            continue
        w = weights.get(feature, 0.0)
        closeness = 1.0 - abs(target - actual)  # 1.0 = perfect fit, 0.0 = worst
        points = closeness * w
        score += points
        reasons.append(f"{feature} fit {closeness:.0%} (+{points:.2f})")

    return score, reasons

def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    Ranks every song against the user's preferences and returns the top `k`.

    Recommending = ranking. We use score_song as the "judge" for every track,
    then sort by score from highest to lowest and keep the best `k`.

    Returns a list of (song, score, explanation) tuples.
    """
    # Score every song. A list comprehension is the Pythonic way to build the
    # (song, score, explanation) records in one pass over the catalog.
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        explanation = "; ".join(reasons) if reasons else "no strong matches"
        scored.append((song, score, explanation))

    # `sorted()` returns a NEW list and leaves `scored` (and `songs`) untouched;
    # `.sort()` would mutate the list in place and return None. We use sorted()
    # so the caller's data isn't reordered as a side effect.
    # key=lambda item: item[1] sorts by the score; reverse=True = highest first.
    ranked = sorted(scored, key=lambda item: item[1], reverse=True)

    # Slicing past the end is safe: if there are fewer than k songs, you just
    # get them all back.
    return ranked[:k]
