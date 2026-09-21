"""
Vercel entry point - api/index.py
Exposes Flask app as serverless function.

Vercel will call this as `app` for each request.
"""
import os
import sys

# Ensure project root is on path (for `app` package)
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app

# Force production config on Vercel
env = os.getenv("FLASK_ENV", "production")
# Mark as Vercel for config (uses /tmp/ems.db)
os.environ["VERCEL"] = "1"

app = create_app(env)

# Vercel expects `app` to be exposed
# For local testing: python api/index.py
if __name__ == "__main__":
    app.run()
