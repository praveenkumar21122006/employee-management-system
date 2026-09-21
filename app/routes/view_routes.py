"""
View Routes - app/routes/view_routes.py
Serves the minimalistic dashboard UI + login/register.
"""
from flask import Blueprint, render_template, redirect, url_for, session
from app.services.auth import get_current_user, login_required

view_bp = Blueprint("views", __name__)

@view_bp.route("/", methods=["GET"])
def index():
    user = get_current_user()
    if not user:
        return redirect(url_for("views.login"))
    return render_template("dashboard.html", user=user.to_dict())

@view_bp.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    user = get_current_user()
    return render_template("dashboard.html", user=user.to_dict() if user else None)

@view_bp.route("/login", methods=["GET"])
def login():
    user = get_current_user()
    if user:
        return redirect(url_for("views.dashboard"))
    return render_template("login.html")

@view_bp.route("/register", methods=["GET"])
def register():
    user = get_current_user()
    if user:
        return redirect(url_for("views.dashboard"))
    return render_template("register.html")

@view_bp.route("/employee", methods=["GET"])
@login_required
def employee_view():
    """Employee-specific view - same dashboard but could be separated."""
    user = get_current_user()
    if user.role == "Admin":
        return redirect(url_for("views.dashboard"))
    return render_template("dashboard.html", user=user.to_dict())

@view_bp.route("/attendance", methods=["GET"])
@login_required
def attendance():
    """Attendance page - timing, name, dept, role"""
    user = get_current_user()
    return render_template("attendance.html", user=user.to_dict() if user else None)
