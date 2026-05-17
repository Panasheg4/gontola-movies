from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify
from app.models import Movie
from app.utils import GENRE_MAP
from app import db
from datetime import date, timedelta
from functools import wraps
import os
import requests as req

admin = Blueprint("admin", __name__, url_prefix="/admin")

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.login"))
        return f(*args, **kwargs)
    return decorated

@admin.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        password = request.form.get("password")
        if password == os.getenv("ADMIN_PASSWORD"):
            session["admin_logged_in"] = True
            return redirect(url_for("admin.dashboard"))
        flash("Wrong password. Try again.")
    return render_template("admin/login.html")

@admin.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.index"))

def _admin_query_params():
    params = {}
    for key in ("page", "q", "status", "genre", "from_date", "to_date"):
        value = request.args.get(key)
        if value:
            params[key] = value
    return params


@admin.route("/dashboard")
@login_required
def dashboard():
    total = Movie.query.count()
    upcoming = Movie.query.filter_by(is_upcoming=True).count()
    trending = Movie.query.filter_by(is_trending=True).count()
    released = Movie.query.filter_by(is_upcoming=False).count()
    recent = Movie.query.order_by(
        Movie.release_date.desc()
    ).limit(5).all()
    return render_template("admin/dashboard.html",
        total=total,
        upcoming=upcoming,
        trending=trending,
        released=released,
        recent=recent
    )

@admin.route("/movies")
@login_required
def movies():
    page = request.args.get("page", 1, type=int)
    query = request.args.get("q", "")
    status = request.args.get("status", "")
    genre = request.args.get("genre", "")
    from_date = request.args.get("from_date", "")
    to_date = request.args.get("to_date", "")

    movie_query = Movie.query

    if query:
        movie_query = movie_query.filter(
            Movie.title.ilike(f"%{query}%")
        )

    if status == "upcoming":
        movie_query = movie_query.filter_by(is_upcoming=True)
    elif status == "released":
        movie_query = movie_query.filter_by(is_upcoming=False)
    elif status == "latest":
        cutoff_date = (date.today() - timedelta(days=150)).isoformat()
        movie_query = movie_query.filter(
            Movie.release_date >= cutoff_date,
            Movie.release_date <= str(date.today()),
            Movie.is_upcoming == False
        )

    if genre:
        if genre == "True stories":
            movie_query = movie_query.filter_by(is_true_story=True)
        else:
            movie_query = movie_query.filter(Movie.genre_names.ilike(f"%{genre}%"))

    if from_date:
        movie_query = movie_query.filter(Movie.release_date >= from_date)
    if to_date:
        movie_query = movie_query.filter(Movie.release_date <= to_date)

    all_movies = movie_query.order_by(
        Movie.release_date.desc()
    ).paginate(page=page, per_page=20, error_out=False)

    genre_choices = sorted(set(GENRE_MAP.values()))

    return render_template("admin/movies.html",
        movies=all_movies,
        query=query,
        status=status,
        genre=genre,
        genre_choices=genre_choices,
        from_date=from_date,
        to_date=to_date
    )


@admin.route("/delete/<int:movie_id>", methods=["GET", "POST"])
@login_required
def delete_movie(movie_id):
    from app.models import BlockedMovieID
    from datetime import date as dt
    movie = Movie.query.get_or_404(movie_id)
    title = movie.title

    already_blocked = BlockedMovieID.query.filter_by(
        tmdb_id=movie_id
    ).first()
    if not already_blocked:
        blocked = BlockedMovieID(
            tmdb_id=movie_id,
            title=title,
            reason="Manually deleted by admin",
            blocked_at=str(dt.today())
        )
        db.session.add(blocked)

    db.session.delete(movie)
    db.session.commit()

    if request.method == "POST":
        return jsonify({"success": True, "id": movie_id})
    return redirect(url_for("admin.movies"))

@admin.route("/bulk-delete", methods=["POST"])
@login_required
def bulk_delete():
    from app.models import BlockedMovieID
    from datetime import date as dt
    data = request.get_json()
    ids = data.get("ids", [])
    deleted = 0
    for mid in ids:
        movie = Movie.query.get(mid)
        if movie:
            already_blocked = BlockedMovieID.query.filter_by(
                tmdb_id=mid
            ).first()
            if not already_blocked:
                blocked = BlockedMovieID(
                    tmdb_id=mid,
                    title=movie.title,
                    reason="Bulk deleted by admin",
                    blocked_at=str(dt.today())
                )
                db.session.add(blocked)
            db.session.delete(movie)
            deleted += 1
    db.session.commit()
    return jsonify({"success": True, "deleted": deleted})

@admin.route("/blocklist")
@login_required
def blocklist():
    from app.models import BlockedMovieID
    blocked = BlockedMovieID.query.order_by(
        BlockedMovieID.blocked_at.desc()
    ).all()
    return render_template(
        "admin/blocklist.html",
        blocked=blocked
    )

@admin.route("/unblock/<int:tmdb_id>")
@login_required
def unblock_movie(tmdb_id):
    from app.models import BlockedMovieID
    blocked = BlockedMovieID.query.filter_by(
        tmdb_id=tmdb_id
    ).first()
    if blocked:
        db.session.delete(blocked)
        db.session.commit()
    return redirect(url_for("admin.blocklist"))

@admin.route("/toggle-true-story/<int:movie_id>")
@login_required
def toggle_true_story(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    movie.is_true_story = not movie.is_true_story
    db.session.commit()
    return redirect(url_for("admin.movies", **_admin_query_params()))

@admin.route("/add")
@login_required
def add_movie():
    return render_template("admin/add_movie.html",
        preview=None,
        error=None
    )

@admin.route("/preview", methods=["POST"])
@login_required
def preview_movie():
    tmdb_id = request.form.get("tmdb_id", "").strip()
    if not tmdb_id or not tmdb_id.isdigit():
        return render_template("admin/add_movie.html",
            error="Please enter a valid TMDB ID number.",
            preview=None
        )
    existing = Movie.query.filter_by(id=int(tmdb_id)).first()
    if existing:
        return render_template("admin/add_movie.html",
            error=f"'{existing.title}' is already in your database!",
            preview=None
        )
    try:
        response = req.get(
            f"https://api.themoviedb.org/3/movie/{tmdb_id}"
            f"?api_key={os.getenv('TMDB_API_KEY')}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8
        )
        data = response.json()
        if "id" not in data:
            return render_template("admin/add_movie.html",
                error=f"No movie found with ID {tmdb_id}.",
                preview=None
            )
        preview = {
            "id": data["id"],
            "title": data["title"],
            "overview": data.get("overview", ""),
            "poster_path": data.get("poster_path", ""),
            "vote_average": data.get("vote_average", 0),
            "vote_count": data.get("vote_count", 0),
            "release_date": data.get("release_date", ""),
            "runtime": data.get("runtime", 0),
            "genre_names": ", ".join(
                g["name"] for g in data.get("genres", [])
            ),
            "tagline": data.get("tagline", ""),
            "adult": data.get("adult", False)
        }
        return render_template("admin/add_movie.html",
            preview=preview,
            error=None
        )
    except Exception as e:
        return render_template("admin/add_movie.html",
            error=f"TMDB error: {e}",
            preview=None
        )

@admin.route("/confirm-add", methods=["POST"])
@login_required
def confirm_add():
    tmdb_id = request.form.get("tmdb_id")
    if not tmdb_id:
        return redirect(url_for("admin.add_movie"))
    existing = Movie.query.filter_by(id=int(tmdb_id)).first()
    if existing:
        return redirect(url_for("admin.movies"))
    try:
        response = req.get(
            f"https://api.themoviedb.org/3/movie/{tmdb_id}"
            f"?api_key={os.getenv('TMDB_API_KEY')}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8
        )
        data = response.json()
        today = str(date.today())
        new_movie = Movie(
            id=int(data["id"]),
            title=data["title"],
            overview=data.get("overview", ""),
            poster_path=data.get("poster_path", ""),
            backdrop_path=data.get("backdrop_path", ""),
            vote_average=float(data.get("vote_average", 0)),
            vote_count=int(data.get("vote_count", 0)),
            release_date=data.get("release_date", ""),
            genre_ids=",".join(
                str(g["id"]) for g in data.get("genres", [])
            ),
            genre_names=", ".join(
                g["name"] for g in data.get("genres", [])
            ),
            is_upcoming=data.get("release_date", "") > today
        )
        db.session.add(new_movie)
        db.session.commit()
        return redirect(
            url_for("admin.movie_added", movie_id=new_movie.id)
        )
    except Exception as e:
        return render_template("admin/add_movie.html",
            error=f"Error saving movie: {e}",
            preview=None
        )

@admin.route("/added/<int:movie_id>")
@login_required
def movie_added(movie_id):
    movie = Movie.query.get_or_404(movie_id)
    return render_template("admin/movie_added.html", movie=movie)

@admin.route("/movie-suggestions")
@login_required
def movie_suggestions():
    query = request.args.get("q", "")
    if len(query) < 2:
        return jsonify([])
    results = Movie.query.filter(
        Movie.title.ilike(f"%{query}%")
    ).limit(8).all()
    return jsonify([{
        "id": m.id,
        "title": m.title,
        "genre_names": m.genre_names or "",
        "vote_average": m.vote_average or 0,
        "release_date": m.release_date or "",
        "poster_path": m.poster_path or ""
    } for m in results])