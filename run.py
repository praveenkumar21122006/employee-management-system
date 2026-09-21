"""
Entry point - run.py

Usage:
  python run.py
  or
  flask --app run run --debug
  or
  gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"
"""
import os
from app import create_app

# Create app with current env
env = os.getenv("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    # Debug only in development
    debug = env == "development"
    print(f"""
╔══════════════════════════════════════════╗
║   Employee Management System (EMS)       ║
║   Flask + SQLite + MVC                   ║
╠══════════════════════════════════════════╣
║   Dashboard: http://localhost:{port}/          ║
║   API:       http://localhost:{port}/employees ║
║   Health:    http://localhost:{port}/health    ║
╚══════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=port, debug=debug)
