import os
import requests
from flask import Blueprint, render_template, request
from app.models import Movie
from app import db
from app.utils import get_genre_names
from datetime import date, timedelta

main = Blueprint("main", __name__)

@main.route("/")
def index():
    today = str(date.today())
    four_months_ago = str(date.today() - timedelta(days=150))
    one_year_ago = str(date.today() - timedelta(days=365))
    four_weeks_ago = str(date.today() - timedelta(weeks=4))

    hero_candidates = Movie.query.filter(
        Movie.is_upcoming == False,
        Movie.vote_average >= 6.5,
        Movie.release_date >= one_year_ago,
        Movie.poster_path != "",
        Movie.poster_path.isnot(None),
        Movie.backdrop_path != "",
        Movie.backdrop_path.isnot(None)
    ).order_by(
        Movie.vote_average.desc(),
        Movie.release_date.desc()
    ).limit(10).all()

    featured = hero_candidates[0] if hero_candidates else None

    if not featured:
        featured = Movie.query.filter(
            Movie.is_upcoming == False
        ).order_by(Movie.release_date.desc()).first()
        if featured:
            hero_candidates = [featured]

    true_stories = Movie.query.filter(
        Movie.is_true_story == True,
        Movie.is_upcoming == False
    ).order_by(
        Movie.vote_average.desc()
    ).limit(20).all()

    recommended = Movie.query.filter(
        Movie.is_upcoming == False,
        Movie.vote_average > 7.0
    ).order_by(
        Movie.vote_average.desc()
    ).limit(20).all()

    # Latest — last 4-5 months
    latest = Movie.query.filter(
        Movie.is_upcoming == False,
        Movie.release_date >= four_months_ago,
        Movie.release_date <= today
    ).order_by(
        Movie.release_date.desc()
    ).limit(20).all()

    # Upcoming — next 4-5 months
    five_months_ahead = str(
        date.today() + timedelta(days=150)
    )
    upcoming = Movie.query.filter(
        Movie.is_upcoming == True,
        Movie.release_date <= five_months_ahead
    ).order_by(
        Movie.release_date.asc()
    ).limit(20).all()

    page = request.args.get('page', 1, type=int)
    all_movies = Movie.query.filter(
        Movie.is_upcoming == False
    ).order_by(
        Movie.release_date.desc(),
        Movie.vote_average.desc()
    ).paginate(page=page, per_page=24, error_out=False)

    try:
        from app.youtube import get_channel_stats, get_shorts
        channel_stats = get_channel_stats()
        shorts = get_shorts(max_results=10)
    except Exception as e:
        print(f"YouTube error: {e}")
        channel_stats = None
        shorts = []

    return render_template("index.html",
        featured=featured,
        hero_candidates=hero_candidates,
        true_stories=true_stories,
        recommended=recommended,
        latest=latest,
        upcoming=upcoming,
        all_movies=all_movies,
        four_weeks_ago=four_weeks_ago,
        channel_stats=channel_stats,
        shorts=shorts
    )

@main.route("/movie/<int:movie_id>")
def movie_detail(movie_id):
    import requests as req
    movie = Movie.query.get_or_404(movie_id)

    # ── FETCH TRAILERS ──
    trailers = []
    try:
        response = req.get(
            f"https://api.themoviedb.org/3/movie"
            f"/{movie_id}/videos"
            f"?api_key={os.getenv('TMDB_API_KEY')}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5
        )
        videos = response.json()
        for video in videos.get("results", []):
            if video["site"] == "YouTube" and \
               video["type"] in [
                   "Trailer", "Teaser",
                   "Clip", "Featurette"
               ]:
                trailers.append({
                    "key": video["key"],
                    "name": video["name"],
                    "type": video["type"]
                })
    except Exception as e:
        print(f"Trailer fetch error: {e}")

    # ── FETCH DIRECTOR, TAGLINE, AGE RATING ──
    director = None
    tagline = None
    age_rating = None
    try:
        detail_res = req.get(
            f"https://api.themoviedb.org/3/movie/{movie_id}"
            f"?api_key={os.getenv('TMDB_API_KEY')}"
            f"&append_to_response=credits,release_dates",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=5
        )
        detail_data = detail_res.json()

        # Director from crew list
        crew = detail_data.get(
            "credits", {}
        ).get("crew", [])
        for person in crew:
            if person.get("job") == "Director":
                director = person["name"]
                break

        # Tagline
        tagline = detail_data.get("tagline", "") or None

        # Age rating — US certification
        release_dates = detail_data.get(
            "release_dates", {}
        ).get("results", [])
        for country in release_dates:
            if country.get("iso_3166_1") == "US":
                dates = country.get("release_dates", [])
                if dates:
                    cert = dates[0].get("certification", "")
                    if cert:
                        age_rating = cert
                break

        # Save to database so we don't re-fetch every time
        changed = False
        if director and movie.director != director:
            movie.director = director
            changed = True
        if tagline and movie.tagline != tagline:
            movie.tagline = tagline
            changed = True
        if age_rating and movie.age_rating != age_rating:
            movie.age_rating = age_rating
            changed = True
        if changed:
            db.session.commit()

    except Exception as e:
        print(f"Detail fetch error: {e}")

    # Use database values as fallback if API fails
    director = director or movie.director
    tagline = tagline or movie.tagline
    age_rating = age_rating or movie.age_rating

    # ── RELATED MOVIES ──
    related = []
    if movie.genre_names:
        first_genre = movie.genre_names.split(',')[0].strip()
        related = Movie.query.filter(
            Movie.id != movie_id,
            Movie.genre_names.ilike(f"%{first_genre}%")
        ).order_by(
            Movie.vote_average.desc()
        ).limit(10).all()

    if not related:
        related = Movie.query.filter(
            Movie.id != movie_id,
            Movie.is_upcoming == False
        ).order_by(
            Movie.vote_average.desc()
        ).limit(10).all()

    return render_template("movie.html",
        movie=movie,
        related=related,
        trailers=trailers,
        director=director,
        tagline=tagline,
        age_rating=age_rating,
        hide_search=True
    )

@main.route("/search")
def search():
    query = request.args.get("q", "").strip()
    four_weeks_ago = str(date.today() - timedelta(weeks=4))
    results = []

    if query:
        local_results = Movie.query.filter(
            Movie.title.ilike(f"%{query}%")
        ).order_by(
            Movie.vote_average.desc()
        ).all()
        results = local_results

        try:
            response = requests.get(
                f"https://api.themoviedb.org/3/search/movie"
                f"?api_key={os.getenv('TMDB_API_KEY')}"
                f"&query={query}",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=5
            )
            data = response.json()
            local_ids = [m.id for m in local_results]
            new_movies_added = 0

            for m in data.get("results", [])[:10]:
                if m["id"] in local_ids:
                    continue
                if 27 in m.get("genre_ids", []):
                    continue
                if m.get("adult", False):
                    continue
                if not m.get("release_date"):
                    continue
                if not m.get("poster_path"):
                    continue

                today_str = str(date.today())
                is_upcoming = m.get(
                    "release_date", ""
                ) > today_str

                # Check permanent blocklist
                from app.models import BlockedMovieID
                from app.utils import is_blocked_movie

                blocked_entry = BlockedMovieID.query.filter_by(
                    tmdb_id=int(m["id"])
                ).first()
                if blocked_entry:
                    continue
                
                # Check content filter
                check = {
                    "adult": m.get("adult", False),
                    "genre_ids": m.get("genre_ids", []),
                    "title": m.get("title", ""),
                    "original_title": m.get("original_title", ""),
                    "original_language": m.get("original_language", "en")
                }
                if is_blocked_movie(check):
                    continue

                existing = Movie.query.filter_by(
                    id=m["id"]
                ).first()
                if existing:
                    local_ids.append(m["id"])
                    if existing not in results:
                        results.append(existing)
                    continue

                new_movie = Movie(
                    id=int(m["id"]),
                    title=m["title"],
                    overview=m.get("overview", ""),
                    poster_path=m.get("poster_path", ""),
                    backdrop_path=m.get("backdrop_path", ""),
                    vote_average=float(
                        m.get("vote_average", 0)
                    ),
                    vote_count=int(
                        m.get("vote_count", 0)
                    ),
                    release_date=m.get("release_date", ""),
                    genre_ids=",".join(
                        str(g) for g in m.get("genre_ids", [])
                    ),
                    genre_names=get_genre_names(
                        m.get("genre_ids", [])
                    ),
                    is_upcoming=is_upcoming
                )
                try:
                    db.session.add(new_movie)
                    db.session.flush()
                    local_ids.append(m["id"])
                    results.append(new_movie)
                    new_movies_added += 1
                except Exception:
                    db.session.rollback()
                    continue

            if new_movies_added > 0:
                db.session.commit()

        except Exception as e:
            print(f"Search TMDB error: {e}")

    return render_template("search.html",
        results=results,
        query=query,
        four_weeks_ago=four_weeks_ago
    )

@main.route("/search/suggestions")
def search_suggestions():
    from flask import jsonify
    query = request.args.get("q", "")
    if len(query) < 2:
        return jsonify([])

    local = Movie.query.filter(
        Movie.title.ilike(f"%{query}%")
    ).limit(5).all()

    suggestions = [{
        "id": m.id,
        "title": m.title,
        "genre_names": m.genre_names or "",
        "vote_average": m.vote_average or 0,
        "poster_path": m.poster_path or ""
    } for m in local]

    if len(local) < 3:
        try:
            response = requests.get(
                f"https://api.themoviedb.org/3/search/movie"
                f"?api_key={os.getenv('TMDB_API_KEY')}"
                f"&query={query}",
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=5
            )
            data = response.json()
            local_ids = [m.id for m in local]

            for m in data.get("results", [])[:8]:
                if m["id"] in local_ids:
                    continue
                if 27 in m.get("genre_ids", []):
                    continue
                if m.get("adult", False):
                    continue
                if not m.get("release_date"):
                    continue
                if not m.get("poster_path"):
                    continue
                
                # Check permanent blocklist
                from app.models import BlockedMovieID
                from app.utils import is_blocked_movie

                blocked_entry = BlockedMovieID.query.filter_by(
                    tmdb_id=int(m["id"])
                ).first()
                if blocked_entry:
                    continue
                
                # Check content filter
                check = {
                    "adult": m.get("adult", False),
                    "genre_ids": m.get("genre_ids", []),
                    "title": m.get("title", ""),
                    "original_title": m.get("original_title", ""),
                    "original_language": m.get("original_language", "en")
                }
                if is_blocked_movie(check):
                    continue

                existing = Movie.query.filter_by(
                    id=m["id"]
                ).first()

                if not existing:
                    today_str = str(date.today())
                    new_movie = Movie(
                        id=int(m["id"]),
                        title=m["title"],
                        overview=m.get("overview", ""),
                        poster_path=m.get("poster_path", ""),
                        backdrop_path=m.get(
                            "backdrop_path", ""
                        ),
                        vote_average=float(
                            m.get("vote_average", 0)
                        ),
                        vote_count=int(
                            m.get("vote_count", 0)
                        ),
                        release_date=m.get(
                            "release_date", ""
                        ),
                        genre_ids=",".join(
                            str(g) for g in
                            m.get("genre_ids", [])
                        ),
                        genre_names=get_genre_names(
                            m.get("genre_ids", [])
                        ),
                        is_upcoming=m.get(
                            "release_date", ""
                        ) > today_str
                    )
                    try:
                        db.session.add(new_movie)
                        db.session.commit()
                        local_ids.append(m["id"])
                    except Exception:
                        db.session.rollback()
                        continue

                suggestions.append({
                    "id": m["id"],
                    "title": m["title"],
                    "genre_names": get_genre_names(
                        m.get("genre_ids", [])
                    ),
                    "vote_average": m.get(
                        "vote_average", 0
                    ),
                    "poster_path": m.get("poster_path", "")
                })

                if len(suggestions) >= 5:
                    break

        except Exception as e:
            print(f"Suggestion error: {e}")

    return jsonify(suggestions)

@main.route("/genre/<genre_name>")
def genre(genre_name):
    genre_display = genre_name.replace(
        "-", " "
    ).title()
    four_weeks_ago = str(
        date.today() - timedelta(weeks=4)
    )
    page = request.args.get('page', 1, type=int)

    movies = Movie.query.filter(
        Movie.genre_names.ilike(f"%{genre_display}%"),
        Movie.is_upcoming == False
    ).order_by(
        Movie.vote_average.desc()
    ).paginate(page=page, per_page=24, error_out=False)

    return render_template("genre.html",
        movies=movies,
        genre_name=genre_display,
        four_weeks_ago=four_weeks_ago
    )

@main.route("/movies/latest")
def latest_movies():
    four_months_ago = str(
        date.today() - timedelta(days=150)
    )
    today = str(date.today())
    four_weeks_ago = str(
        date.today() - timedelta(weeks=4)
    )
    page = request.args.get('page', 1, type=int)

    movies = Movie.query.filter(
        Movie.is_upcoming == False,
        Movie.release_date >= four_months_ago,
        Movie.release_date <= today
    ).order_by(
        Movie.release_date.desc()
    ).paginate(page=page, per_page=24, error_out=False)

    return render_template("movie_list.html",
        movies=movies,
        title="Latest Movies",
        four_weeks_ago=four_weeks_ago
    )

@main.route("/movies/recommended")
def recommended_movies():
    four_weeks_ago = str(
        date.today() - timedelta(weeks=4)
    )
    page = request.args.get('page', 1, type=int)

    movies = Movie.query.filter(
        Movie.is_upcoming == False,
        Movie.vote_average > 7.0
    ).order_by(
        Movie.vote_average.desc()
    ).paginate(page=page, per_page=24, error_out=False)

    return render_template("movie_list.html",
        movies=movies,
        title="Recommended For You",
        four_weeks_ago=four_weeks_ago
    )

@main.route("/movies/upcoming")
def upcoming_movies():
    four_weeks_ago = str(
        date.today() - timedelta(weeks=4)
    )
    five_months_ahead = str(
        date.today() + timedelta(days=150)
    )
    page = request.args.get('page', 1, type=int)

    movies = Movie.query.filter(
        Movie.is_upcoming == True,
        Movie.release_date <= five_months_ahead
    ).order_by(
        Movie.release_date.asc()
    ).paginate(page=page, per_page=24, error_out=False)

    return render_template("movie_list.html",
        movies=movies,
        title="Upcoming Movies",
        four_weeks_ago=four_weeks_ago
    )

@main.route("/shorts")
def shorts_page():
    from app.youtube import (
        get_shorts, get_channel_stats, format_number
    )
    shorts = get_shorts(max_results=30)
    channel_stats = get_channel_stats()
    return render_template("shorts.html",
        shorts=shorts,
        channel_stats=channel_stats,
        hide_search=True,
        format_number=format_number
    )


@main.route("/true-stories")
def true_stories():
    four_weeks_ago = str(date.today() - timedelta(weeks=4))
    page = request.args.get('page', 1, type=int)

    movies = Movie.query.filter(
        Movie.is_true_story == True,
        Movie.is_upcoming == False
    ).order_by(
        Movie.vote_average.desc()
    ).paginate(page=page, per_page=24, error_out=False)

    return render_template("movie_list.html",
        movies=movies,
        title="Based on True Stories",
        four_weeks_ago=four_weeks_ago
    )

@main.route("/about")
def about():
    try:
        from app.youtube import get_channel_stats
        channel_stats = get_channel_stats()
    except:
        channel_stats = None
    return render_template("about.html",
        channel_stats=channel_stats,
        hide_search=True
    )