import os
from dotenv import load_dotenv
load_dotenv()

from app import create_app, db
from app import models

app = create_app()

with app.app_context():
    db.create_all()
    print("Database tables ready!")

def start_scheduler():
    from apscheduler.schedulers.background import BackgroundScheduler
    import atexit

    def scheduled_fetch():
        print("Scheduler: Running fetch...")
        with app.app_context():
            try:
                import sys
                sys.path.insert(0, '.')
                from scripts.fetch_movies import run_all
                run_all(full_refresh=False)
                print("Scheduler: Done!")
            except Exception as e:
                print(f"Scheduler error: {e}")

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=scheduled_fetch,
        trigger="interval",
        hours=24,
        id="movie_fetch"
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown())
    print("Scheduler running — updates every 24hrs!")

if __name__ == "__main__":
    start_scheduler()
    app.run(debug=True)