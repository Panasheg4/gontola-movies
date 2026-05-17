from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    db.init_app(app)

    from datetime import datetime
    from app.youtube import format_number

    @app.template_filter('format_number')
    def format_number_filter(num):
        return format_number(num)

    @app.template_filter('format_date')
    def format_date_filter(date_str):
        try:
            dt = datetime.strptime(str(date_str), "%Y-%m-%d")
            return dt.strftime("%d %B %Y")
        except:
            return date_str
        
    @app.context_processor
    def inject_channel_stats():
        try:
            from app.youtube import get_channel_stats
            stats = get_channel_stats()
            return {"channel_stats": stats}
        except Exception:
            return {"channel_stats": None}

    from app.routes import main
    app.register_blueprint(main)

    from app.admin import admin
    app.register_blueprint(admin)

    return app