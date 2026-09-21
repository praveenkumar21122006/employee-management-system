"""
Department Routes - app/routes/department_routes.py
"""
from flask import Blueprint, request
from app.controllers.department_controller import DepartmentController
from app.services.auth import login_required, admin_required

department_bp = Blueprint("departments", __name__, url_prefix="/departments")

@department_bp.route("", methods=["GET"])
def list_departments():
    """GET /departments - Public (needed for registration dropdown) - returns departments without auth"""
    return DepartmentController.get_all()

@department_bp.route("", methods=["POST"])
@admin_required
def create_department():
    """POST /departments - Admin only"""
    data = request.get_json(silent=True) or {}
    return DepartmentController.create(data)

@department_bp.route("/<int:dept_id>", methods=["PUT"])
@admin_required
def update_department(dept_id):
    """PUT /departments/{id} - Admin only"""
    data = request.get_json(silent=True) or {}
    return DepartmentController.update(dept_id, data)

@department_bp.route("/<int:dept_id>", methods=["DELETE"])
@admin_required
def delete_department(dept_id):
    """DELETE /departments/{id} - Admin only"""
    return DepartmentController.delete(dept_id)
