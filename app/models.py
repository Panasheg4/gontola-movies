from app import db

class Movie(db.Model):
    __tablename__ = "movies"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    overview = db.Column(db.Text, nullable=True)
    poster_path = db.Column(db.String(200), nullable=True)
    backdrop_path = db.Column(db.String(200), nullable=True)
    vote_count = db.Column(db.Integer, default=0)
    vote_average = db.Column(db.Float, nullable=True)
    release_date = db.Column(db.String(20), nullable=True)
    is_trending = db.Column(db.Boolean, default=False)
    genre_ids = db.Column(db.String(100), nullable=True)
    genre_names = db.Column(db.String(200), nullable=True)
    is_upcoming = db.Column(db.Boolean, default=False)
    is_true_story = db.Column(db.Boolean, default=False)
    tagline = db.Column(db.String(300), nullable=True)
    director = db.Column(db.String(100), nullable=True)
    age_rating = db.Column(db.String(20), nullable=True)


class BlockedMovieID(db.Model):
    __tablename__ = "blocked_movie_ids"
    
    id = db.Column(db.Integer, primary_key=True)
    tmdb_id = db.Column(db.Integer, unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=True)
    reason = db.Column(db.String(200), nullable=True)
    blocked_at = db.Column(db.String(20), nullable=True)
    