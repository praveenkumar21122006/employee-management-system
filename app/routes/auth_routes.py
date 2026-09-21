"""
Auth Routes - app/routes/auth_routes.py
"""
from flask import Blueprint, request
from app.controllers.auth_controller import AuthController
from app.services.auth import login_required

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

@auth_bp.route("/register", methods=["POST"])
def register():
    """
    POST /auth/register
    Body: { first_name, last_name, email, password, salary, role?, department_id?, phone?, hire_date? }
    Public can self-register as Employee; Admin can create Admins when logged in.
    """
    data = request.get_json(silent=True) or {}
    return AuthController.register(data)

@auth_bp.route("/login", methods=["POST"])
def login():
    """
    POST /auth/login
    Body: { email, password }
    """
    data = request.get_json(silent=True) or {}
    return AuthController.login(data)

@auth_bp.route("/logout", methods=["POST"])
def logout():
    """POST /auth/logout"""
    return AuthController.logout()

@auth_bp.route("/me", methods=["GET"])
def me():
    """GET /auth/me -> current user"""
    return AuthController.me()
