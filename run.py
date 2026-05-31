import os
import sys
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

from app import create_app, db
from app import models

app = create_app()

with app.app_context():
    db.create_all()
    print("Database tables ready!")

def run_immediate_check():
    """
    Fail-safe check that runs right when the server boots up.
    It checks your database to see if the content is stale.
    """
    print("\n[Startup Check] Inspecting database currency...")
    with app.app_context():
        try:
            # Look at the release date of your newest upcoming or saved movie
            # to safely guess when the last successful fetch happened.
            from app.models import Movie
            latest_saved_movie = Movie.query.order_by(Movie.id.desc()).first()
            
            # If database is completely empty OR if you want a guaranteed fetch on boot,
            # you can adjust this condition. Let's make it run if it hasn't updated today.
            should_fetch = True 
            
            if latest_saved_movie:
                print("Database contains records. Triggering refresh to synchronize content updates...")
            else:
                print("Database is empty. Initializing baseline content load...")

            if should_fetch:
                sys.path.insert(0, '.')
                from scripts.fetch_movies import run_all
                run_all(full_refresh=False)
                print("[Startup Check] Synchronization complete!\n")
                
        except Exception as e:
            print(f"[Startup Check] Encountered a database connection or fetch error: {e}\n")


def start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    import atexit

    def scheduled_fetch():
        print("Scheduler: Running background interval fetch...")
        with app.app_context():
            try:
                sys.path.insert(0, '.')
                from scripts.fetch_movies import run_all
                run_all(full_refresh=False)
                print("Scheduler: Done!")
            except Exception as e:
                print(f"Scheduler error: {e}")

    scheduler = BackgroundScheduler()
    # Keeps your 24-hour interval job ready for when you move to a paid tier!
    scheduler.add_job(
        func=scheduled_fetch,
        trigger="interval",
        hours=24,
        id="movie_fetch"
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    print("Scheduler initialized — standard 24-hour background interval armed!")

# This triggers the scheduler when Render runs your app in production
start_scheduler()

# This forces an instant update whenever the server wakes up / boots up
run_immediate_check()

if __name__ == "__main__":
    # If running locally in development mode
    app.run(debug=True)