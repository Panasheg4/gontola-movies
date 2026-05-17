import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import requests
from dotenv import load_dotenv
from datetime import date
from app import create_app, db
from app.models import Movie
from app.utils import get_genre_names, is_blocked_movie

load_dotenv()
API_KEY = os.getenv("TMDB_API_KEY")
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
BASE_URL = "https://api.themoviedb.org/3"

def save_movie(movie_data, is_upcoming=False, is_true_story=False):
    from app.models import BlockedMovieID

    # Check permanent blocklist first
    blocked = BlockedMovieID.query.filter_by(
        tmdb_id=int(movie_data["id"])
    ).first()
    if blocked:
        return  

    existing = Movie.query.filter_by(id=movie_data["id"]).first()
    if existing:
        existing.title = movie_data["title"]
        existing.overview = movie_data["overview"]
        existing.poster_path = movie_data["poster_path"]
        existing.backdrop_path = movie_data.get("backdrop_path", "")
        existing.vote_average = float(movie_data["vote_average"])
        existing.vote_count = int(movie_data.get("vote_count", 0))
        existing.release_date = movie_data["release_date"]
        existing.genre_ids = movie_data["genre_ids"]
        existing.genre_names = movie_data["genre_names"]
        existing.is_upcoming = is_upcoming
        if is_true_story:
            existing.is_true_story = True
    else:
        movie = Movie(
            id=int(movie_data["id"]),
            title=movie_data["title"],
            overview=movie_data["overview"],
            poster_path=movie_data["poster_path"],
            backdrop_path=movie_data.get("backdrop_path", ""),
            vote_average=float(movie_data["vote_average"]),
            vote_count=int(movie_data.get("vote_count", 0)),
            release_date=movie_data["release_date"],
            genre_ids=movie_data["genre_ids"],
            genre_names=movie_data["genre_names"],
            is_upcoming=is_upcoming,
            is_true_story=is_true_story
        )
        db.session.add(movie)


def has_valid_rating(movie):
    try:
        return float(movie.get("vote_average", 0) or 0) >= 5.0
    except (TypeError, ValueError):
        return False


def fetch_trending_movies():
    print("Fetching trending movies...")
    response = requests.get(
        f"{BASE_URL}/trending/movie/week?api_key={API_KEY}&include_adult=false",
        headers=headers,
        timeout=10
    )
    data = response.json()
    count = 0
    for movie in data["results"]:
        if movie.get("adult", False):
            continue
        if is_blocked_movie(movie):
            continue
        if not has_valid_rating(movie):
            continue
        clean_movie = {
            "id": movie["id"],
            "title": movie["title"],
            "overview": movie["overview"],
            "poster_path": movie.get("poster_path", ""),
            "backdrop_path": movie.get("backdrop_path", ""),
            "vote_count": int(movie.get("vote_count", 0)),
            "vote_average": float(movie["vote_average"]),
            "release_date": movie["release_date"],
            "genre_ids": ",".join(str(gid) for gid in movie["genre_ids"]),
            "genre_names": get_genre_names(movie["genre_ids"])
        }
        save_movie(clean_movie, is_upcoming=False)
        count += 1
    print(f"Saved {count} trending movies!")

def fetch_upcoming_movies():
    print("Fetching upcoming movies...")
    from datetime import date, timedelta
    today = str(date.today())
    six_months = str(date.today() + timedelta(days=180))
    count = 0

    for page in range(1, 8):
        response = requests.get(
            f"{BASE_URL}/movie/upcoming"
            f"?api_key={API_KEY}&include_adult=false&page={page}",
            headers=headers,
            timeout=10
        )
        data = response.json()
        if not data.get("results"):
            break
        for movie in data["results"]:
            if movie.get("adult", False):
                continue
            if is_blocked_movie(movie):
                continue
            if not movie["release_date"]:
                continue
            if movie["release_date"] <= today:
                continue
            if movie["release_date"] > six_months:
                continue
            clean_movie = {
                "id": movie["id"],
                "title": movie["title"],
                "overview": movie["overview"],
                "poster_path": movie.get("poster_path", ""),
                "backdrop_path": movie.get("backdrop_path", ""),
                "vote_average": float(
                    movie.get("vote_average", 0)
                ),
                "vote_count": int(
                    movie.get("vote_count", 0)
                ),
                "release_date": movie["release_date"],
                "genre_ids": ",".join(
                    str(gid) for gid in movie["genre_ids"]
                ),
                "genre_names": get_genre_names(
                    movie["genre_ids"]
                ),
                "is_true_story": False
            }
            save_movie(clean_movie, is_upcoming=True)
            count += 1
    print(f"Saved {count} upcoming movies!")

def fix_upcoming_flags():
    print("Fixing upcoming flags...")
    today = str(date.today())
    all_movies = Movie.query.all()
    fixed = 0
    for movie in all_movies:
        correct_flag = movie.release_date > today
        if movie.is_upcoming != correct_flag:
            movie.is_upcoming = correct_flag
            fixed += 1
    print(f"Fixed {fixed} movies!")

def fetch_discover_movies(pages=50):
    print("Fetching discover movies...")
    count = 0
    for page in range(1, pages + 1):
        response = requests.get(
            f"{BASE_URL}/discover/movie"
            f"?api_key={API_KEY}"
            f"&sort_by=popularity.desc"
            f"&vote_count.gte=500"
            f"&vote_average.gte=5.0"
            f"&without_genres=27,10749"
            f"&include_adult=false"
            f"&with_original_language=en"
            f"&page={page}",
            headers=headers,
            timeout=10
        )
        data = response.json()
        if not data.get("results"):
            break
        for movie in data["results"]:
            if movie.get("adult", False):
                continue
            if is_blocked_movie(movie):
                continue
            if not has_valid_rating(movie):
                continue
            if not movie.get("release_date"):
                continue
            clean_movie = {
                "id": movie["id"],
                "title": movie["title"],
                "overview": movie["overview"],
                "poster_path": movie.get("poster_path", ""),
                "backdrop_path": movie.get("backdrop_path", ""),
                "vote_average": float(movie["vote_average"]),
                "vote_count": int(movie.get("vote_count", 0)),
                "release_date": movie["release_date"],
                "genre_ids": ",".join(
                    str(gid) for gid in movie["genre_ids"]
                ),
                "genre_names": get_genre_names(
                    movie["genre_ids"]
                ),
                "is_true_story": False
            }
            save_movie(clean_movie, is_upcoming=False)
            count += 1
        print(f"Page {page} done — {count} total so far...")
    print(f"Fetched {count} discover movies!")

def fetch_movie_by_id(tmdb_id):
    print(f"Fetching movie ID {tmdb_id}...")
    response = requests.get(
        f"{BASE_URL}/movie/{tmdb_id}?api_key={API_KEY}",
        headers=headers,
        timeout=10
    )
    movie = response.json()
    
    if "id" not in movie:
        print(f"  Not found on TMDB!")
        return

    # Build genre_ids list for blocking check
    genre_ids = [g["id"] for g in movie.get("genres", [])]
    check = {
        "adult": movie.get("adult", False),
        "genre_ids": genre_ids,
        "title": movie.get("title", ""),
        "original_title": movie.get("original_title", ""),
        "overview": movie.get("overview", "")
    }

    if is_blocked_movie(check):
        print(f"  Blocked: {movie['title']}")
        return

    if float(movie.get("vote_average", 0) or 0) < 5.0:
        print(f"  Skipping low-rated movie: {movie.get('title', 'unknown')}")
        return

    clean_movie = {
        "id": movie["id"],
        "title": movie["title"],
        "overview": movie.get("overview", ""),
        "poster_path": movie.get("poster_path", ""),
        "backdrop_path": movie.get("backdrop_path", ""),
        "vote_count": int(movie.get("vote_count", 0)),
        "vote_average": float(movie.get("vote_average", 0)),
        "release_date": movie.get("release_date", ""),
        "genre_ids": ",".join(str(g["id"]) for g in movie.get("genres", [])),
        "genre_names": ", ".join(g["name"] for g in movie.get("genres", []))
    }

    today = str(date.today())
    is_upcoming = clean_movie["release_date"] > today

    existing = Movie.query.filter_by(id=clean_movie["id"]).first()
    if existing:
        print(f"  Already exists: {movie['title']}")
        return

    new_movie = Movie(
        id=int(clean_movie["id"]),
        title=clean_movie["title"],
        overview=clean_movie["overview"],
        poster_path=clean_movie["poster_path"],
        backdrop_path=clean_movie["backdrop_path"],
        vote_average=clean_movie["vote_average"],
        release_date=clean_movie["release_date"],
        genre_ids=clean_movie["genre_ids"],
        genre_names=clean_movie["genre_names"],
        is_upcoming=is_upcoming
    )
    db.session.add(new_movie)
    print(f"  Saved: {movie['title']}")

def clean_blocked_movies():
    print("Cleaning blocked movies from database...")
    removed = 0
    all_movies = Movie.query.all()

    for movie in all_movies:
        if is_blocked_movie(movie):
            print(f"  Removing blocked movie: {movie.title}")
            db.session.delete(movie)
            removed += 1

    if removed > 0:
        db.session.commit()

    print(f"Removed {removed} blocked movies!")


def fetch_true_story_movies(pages=10):
    print("Fetching true story movies...")
    count = 0

    def safe_save(movie_data, genre_ids):
        clean_movie = {
            "id": movie_data["id"],
            "title": movie_data["title"],
            "overview": movie_data["overview"],
            "poster_path": movie_data.get("poster_path", ""),
            "backdrop_path": movie_data.get("backdrop_path", ""),
            "vote_average": float(movie_data.get("vote_average", 0)),
            "vote_count": int(movie_data.get("vote_count", 0)),
            "release_date": movie_data["release_date"],
            "genre_ids": ",".join(str(gid) for gid in genre_ids),
            "genre_names": get_genre_names(genre_ids),
            "is_true_story": True
        }
        save_movie(
            clean_movie,
            is_upcoming=False,
            is_true_story=True
        )
        return True

    def is_pure_fantasy_sci_fi_animation(genre_ids):
        return all(g in [14, 878, 16, 27] for g in genre_ids)

    def has_true_story_signal(genre_ids):
        return 36 in genre_ids or 99 in genre_ids or 18 in genre_ids

    # Fetch History genre movies
    for page in range(1, pages + 1):
        response = requests.get(
            f"{BASE_URL}/discover/movie"
            f"?api_key={API_KEY}"
            f"&with_genres=36"
            f"&sort_by=popularity.desc"
            f"&vote_count.gte=100"
            f"&include_adult=false"
            f"&with_original_language=en"
            f"&page={page}",
            headers=headers,
            timeout=10
        )
        data = response.json()
        if not data.get("results"):
            break
        for movie in data["results"]:
            if movie.get("adult", False):
                continue
            if is_blocked_movie(movie):
                continue
            if not has_valid_rating(movie):
                continue
            if not movie.get("release_date"):
                continue
            genre_ids = movie.get("genre_ids", [])
            if is_pure_fantasy_sci_fi_animation(genre_ids):
                continue
            if safe_save(movie, genre_ids):
                count += 1
        print(f"History page {page} done...")

    # Fetch Documentary genre movies
    for page in range(1, pages + 1):
        response = requests.get(
            f"{BASE_URL}/discover/movie"
            f"?api_key={API_KEY}"
            f"&with_genres=99"
            f"&sort_by=popularity.desc"
            f"&vote_count.gte=100"
            f"&include_adult=false"
            f"&with_original_language=en"
            f"&page={page}",
            headers=headers,
            timeout=10
        )
        data = response.json()
        if not data.get("results"):
            break
        for movie in data["results"]:
            if movie.get("adult", False):
                continue
            if is_blocked_movie(movie):
                continue
            if not has_valid_rating(movie):
                continue
            if not movie.get("release_date"):
                continue
            genre_ids = movie.get("genre_ids", [])
            if is_pure_fantasy_sci_fi_animation(genre_ids):
                continue
            if safe_save(movie, genre_ids):
                count += 1
        print(f"Documentary page {page} done...")

    # Fetch keyword 10614 with drama and strict filtering
    for page in range(1, pages + 1):
        response = requests.get(
            f"{BASE_URL}/discover/movie"
            f"?api_key={API_KEY}"
            f"&with_keywords=10614"
            f"&without_genres=16,878,14,27,10751"
            f"&sort_by=vote_count.desc"
            f"&vote_count.gte=200"
            f"&include_adult=false"
            f"&with_original_language=en"
            f"&page={page}",
            headers=headers,
            timeout=10
        )
        data = response.json()
        if not data.get("results"):
            break
        for movie in data["results"]:
            if movie.get("adult", False):
                continue
            if is_blocked_movie(movie):
                continue
            if not has_valid_rating(movie):
                continue
            if not movie.get("release_date"):
                continue
            genre_ids = movie.get("genre_ids", [])
            if not has_true_story_signal(genre_ids):
                continue
            if is_pure_fantasy_sci_fi_animation(genre_ids):
                continue
            if safe_save(movie, genre_ids):
                count += 1
        print(f"Keyword page {page} done...")

    print(f"Fetched {count} true story movies!")


def run_all(full_refresh=False):
    app = create_app()
    with app.app_context():
        fetch_trending_movies()
        db.session.commit()
        fetch_upcoming_movies()
        db.session.commit()

        pages = 50 if full_refresh else 10
        fetch_discover_movies(pages=pages)
        db.session.commit()

        fetch_true_story_movies(pages=10)
        db.session.commit()
        fix_upcoming_flags()
        db.session.commit()
        clean_blocked_movies()
        db.session.commit()

        total = Movie.query.count()
        upcoming = Movie.query.filter_by(
            is_upcoming=True
        ).count()
        true_story = Movie.query.filter_by(
            is_true_story=True
        ).count()
        print(f"\nDatabase summary:")
        print(f"  Total: {total}")
        print(f"  Upcoming: {upcoming}")
        print(f"  True Stories: {true_story}")
        print(f"  Released: {total - upcoming}")
        print("All done!")

# Change this line at the very bottom:
run_all(full_refresh=True)