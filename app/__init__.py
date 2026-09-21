"""
Application Factory - app/__init__.py

Implements Flask application factory pattern (MVC entry point).
Handles DB initialization, blueprint registration, and graceful error handling.
Adds session-based auth with role separation (Admin/Employee).
"""
import os
import logging
from datetime import timedelta
from flask import Flask, jsonify, session, redirect, url_for, request
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from sqlalchemy.exc import OperationalError
from sqlalchemy import text, inspect

from app.config import config_by_name

# Initialize extensions (unbound)
db = SQLAlchemy()

def create_app(env: str = None) -> Flask:
    """
    Create and configure Flask application.
    :param env: 'development' or 'production'
    """
    env = env or os.getenv("FLASK_ENV", "development")
    app = Flask(__name__, 
                template_folder="views/templates", 
                static_folder="views/static")
    
    app.config.from_object(config_by_name.get(env, config_by_name["development"]))
    # Session config for auth
    app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    # CORS with credentials for session cookies
    CORS(app, supports_credentials=True)

    # Setup logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Init extensions
    db.init_app(app)

    # Import models to ensure they are registered with SQLAlchemy
    with app.app_context():
        from app.models import employee, department, attendance  # noqa: F401
        
        # Attempt DB creation with graceful handling
        try:
            db.create_all()
            # --- Migration: add password_hash column if missing (for existing DBs) ---
            _ensure_password_column(app)
            logger.info("Database tables verified/created successfully.")
            # Seed default departments if empty
            _seed_initial_data(app)
            # Seed default admin if no users
            _seed_default_admin(app)
        except OperationalError as e:
            logger.error(f"Database connection failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during DB init: {e}")

    # Register blueprints (Controller -> Routes)
    from app.routes.employee_routes import employee_bp
    from app.routes.department_routes import department_bp
    from app.routes.view_routes import view_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.attendance_routes import attendance_bp

    app.register_blueprint(employee_bp)
    app.register_blueprint(department_bp)
    app.register_blueprint(view_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(attendance_bp)

    # Global error handlers - prevent crashes on DB errors
    @app.errorhandler(OperationalError)
    def handle_db_error(e):
        logger.error(f"Database operational error: {e}")
        return jsonify({"error": "Database unavailable. Please try again later.", "details": str(e)}), 503

    @app.errorhandler(404)
    def handle_404(e):
        # For API routes return JSON, for browser return redirect
        if request.path.startswith("/api") or request.path.startswith("/employees") or request.path.startswith("/departments") or request.path.startswith("/auth"):
            return jsonify({"error": "Resource not found"}), 404
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(401)
    def handle_401(e):
        return jsonify({"error": "Authentication required"}), 401

    @app.errorhandler(403)
    def handle_403(e):
        return jsonify({"error": "Forbidden"}), 403

    @app.errorhandler(500)
    def handle_500(e):
        logger.error(f"Internal server error: {e}")
        return jsonify({"error": "Internal server error"}), 500

    @app.route("/health", methods=["GET"])
    def health_check():
        """Lightweight health check endpoint."""
        try:
            db.session.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as ex:
            db_status = f"disconnected: {ex}"
        return jsonify({"status": "ok", "database": db_status}), 200

    @app.context_processor
    def inject_user():
        """Make current user available in templates."""
        from app.services.auth import get_current_user
        try:
            user = get_current_user()
            return dict(current_user=user)
        except Exception:
            return dict(current_user=None)

    return app


def _ensure_password_column(app):
    """Add password_hash column if DB was created before auth feature."""
    try:
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        cols = [c["name"] for c in inspector.get_columns("employees")]
        if "password_hash" not in cols:
            app.logger.info("Migrating DB: adding password_hash column...")
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE employees ADD COLUMN password_hash VARCHAR(255)"))
            app.logger.info("Migration complete: password_hash added.")
    except Exception as e:
        app.logger.warning(f"Migration check failed: {e}")

def _seed_initial_data(app):
    """Seed default departments if none exist."""
    from app.models.department import Department
    if Department.query.count() == 0:
        defaults = [
            Department(department_name="Engineering", manager_id=None),
            Department(department_name="Human Resources", manager_id=None),
            Department(department_name="Marketing", manager_id=None),
            Department(department_name="Finance", manager_id=None),
        ]
        try:
            db.session.bulk_save_objects(defaults)
            db.session.commit()
            app.logger.info("Seeded default departments.")
        except Exception as e:
            db.session.rollback()
            app.logger.warning(f"Seeding failed: {e}")

def _seed_default_admin(app):
    """Ensure demo admin/employee exist and backfill passwords."""
    from app.models.employee import Employee
    try:
        # Backfill missing passwords first
        missing = Employee.query.filter((Employee.password_hash == None) | (Employee.password_hash == "")).all()
        for u in missing:
            u.set_password("changeme123")
            app.logger.info(f"Set default password for {u.email} -> changeme123")
        if missing:
            db.session.commit()

        # Create ONE admin account once (if no admin exists) - no demo employee auto-created
        # Includes requested admin oggyprime6@gmail.com for Vercel deployment
        demos = [
            ("admin@ems.local", "Admin", "User", "555-0100", 120000, "Admin", "admin123"),
            ("oggyprime6@gmail.com", "Oggy", "Prime", "555-0100", 120000, "Admin", "21122006"),
        ]
        created = []
        for email, fn, ln, phone, salary, role, pwd in demos:
            if not Employee.query.filter_by(email=email).first():
                emp = Employee(first_name=fn, last_name=ln, email=email, phone=phone, salary=salary, role=role, department_id=1)
                emp.set_password(pwd)
                db.session.add(emp)
                created.append(email)
        if created:
            db.session.commit()
            app.logger.info(f"Seeded demo users: {', '.join(created)}")
        elif Employee.query.count() == 0:
            # Fallback if totally empty and loop above failed
            pass
    except Exception as e:
        db.session.rollback()
        app.logger.warning(f"Admin seeding failed: {e}")
