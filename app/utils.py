import unicodedata

GENRE_MAP = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Science Fiction",
    53: "Thriller",
    10770: "TV Movie",
    37: "Western",
    27: "Horror",
    10752: "War",
    10759: "Action & Adventure",
    10762: "Kids",
    10763: "News",
    10764: "Reality",
    10765: "Sci-Fi & Fantasy",
    10766: "Soap",
    10767: "Talk",
    10768: "War & Politics",
}

def get_genre_names(genre_id_list):
    return ", ".join([
        GENRE_MAP.get(gid, "Unknown")
        for gid in genre_id_list
    ])

# Only exact title-level blocks — not overview
BLOCKED_KEYWORDS = [
    "pornhub",
    "porn",
    "xxx",
    "nymphomaniac",
    "hotel desire",
    "hot girls wanted",
    "from straight a's to xxx",
    "money shot",
    "after porn ends",
    "onlyfans",
    "malena",
]

ALLOWED_JAPANESE = [
    "demon slayer", "infinity castle",
    "chainsaw man", "your name",
    "spirited away", "princess mononoke",
    "akira", "ghost in the shell",
    "howl's moving castle", "my neighbor totoro",
    "dragon ball super", "one piece film",
    "jujutsu kaisen"
]

def normalize_text(value):
    if not value:
        return ""
    text = str(value).strip().lower()
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(
        char for char in normalized
        if not unicodedata.combining(char)
    )

def get_field(movie, key, default=""):
    if isinstance(movie, dict):
        return movie.get(key, default)
    return getattr(movie, key, default) \
        if hasattr(movie, key) else default

def is_allowed_japanese_movie(title, original_title):
    for allowed in ALLOWED_JAPANESE:
        if allowed in title or allowed in original_title:
            return True
    return False

def contains_blocked_text(text):
    if not text:
        return False
    lowered = normalize_text(text)
    for keyword in BLOCKED_KEYWORDS:
        if keyword in lowered:
            return True
    return False

def is_blocked_movie(movie):
    # Block TMDB adult flag
    adult = get_field(movie, "adult", False)
    if str(adult).lower() in ["true", "1"]:
        return True

    # Get genre IDs
    raw_genre_ids = get_field(movie, "genre_ids", [])
    if isinstance(raw_genre_ids, str):
        genre_ids = [
            int(g.strip())
            for g in raw_genre_ids.split(",")
            if g.strip().isdigit()
        ]
    elif isinstance(raw_genre_ids, list):
        genre_ids = [int(g) for g in raw_genre_ids
                     if str(g).isdigit()]
    else:
        genre_ids = []

    # Block horror always
    if 27 in genre_ids:
        return True

    # Block pure romance only
    if genre_ids == [10749]:
        return True

    title = normalize_text(get_field(movie, "title", ""))
    original_title = normalize_text(
        get_field(movie, "original_title", "")
    )

    # Allow whitelisted Japanese/anime movies
    if is_allowed_japanese_movie(title, original_title):
        return False

    # Block non-English except Japanese
    lang = get_field(movie, "original_language", "en")
    if lang not in ["en", "ja"]:
        return True

    # Block by title only — NOT overview
    if contains_blocked_text(title):
        return True
    if contains_blocked_text(original_title):
        return True

    return False