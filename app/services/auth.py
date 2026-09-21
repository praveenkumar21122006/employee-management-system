"""
Auth Service - app/services/auth.py

Session-based authentication helpers + decorators for role-based access.
"""
from functools import wraps
from flask import session, jsonify, request, redirect, url_for, g

from app.models.employee import Employee

def get_current_user():
    """Return Employee instance for current session or None."""
    uid = session.get("user_id")
    if not uid:
        return None
    # Use db session via model query; import avoids circular
    return Employee.query.get(uid)

def login_user(user: Employee):
    """Persist user in session."""
    session.clear()
    session["user_id"] = user.id
    session["role"] = user.role
    session["email"] = user.email
    session.permanent = True

def logout_user():
    session.clear()

def login_required(f):
    """Decorator: requires authentication. Returns 401 JSON for API, redirect for browser."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            # If browser expects HTML, redirect to login
            if request.accept_mimetypes.best == "text/html" or "text/html" in request.headers.get("Accept",""):
                return redirect(url_for("views.login"))
            return jsonify({"error": "Authentication required", "code": "unauthorized"}), 401
        # expose to view
        g.current_user = user
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    """Decorator: requires Admin role."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.accept_mimetypes.best == "text/html" or "text/html" in request.headers.get("Accept",""):
                return redirect(url_for("views.login"))
            return jsonify({"error": "Authentication required"}), 401
        if user.role != "Admin":
            return jsonify({"error": "Admin privileges required", "code": "forbidden"}), 403
        g.current_user = user
        return f(*args, **kwargs)
    return decorated

def is_admin():
    user = get_current_user()
    return user and user.role == "Admin"
