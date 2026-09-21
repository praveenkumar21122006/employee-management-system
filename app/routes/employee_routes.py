"""
Employee Routes - app/routes/employee_routes.py

Defines API endpoints (View -> Controller). All routes prefixed with /employees
Role-based access: Admin full, Employee read + self-update.
"""
from flask import Blueprint, request
from app.controllers.employee_controller import EmployeeController
from app.services.auth import login_required, admin_required

employee_bp = Blueprint("employees", __name__, url_prefix="/employees")

@employee_bp.route("", methods=["POST"])
@admin_required
def create_employee():
    """
    POST /employees - Admin only
    Create a new employee. Expects JSON including optional password.
    """
    data = request.get_json(silent=True) or {}
    return EmployeeController.create_employee(data)

@employee_bp.route("", methods=["GET"])
@login_required
def list_employees():
    """
    GET /employees - Any authenticated user
    Optional query params: department, department_id, search
    """
    return EmployeeController.get_all_employees(request.args)

@employee_bp.route("/<int:emp_id>", methods=["GET"])
@login_required
def get_employee(emp_id):
    """GET /employees/{id} - Any authenticated"""
    return EmployeeController.get_employee_by_id(emp_id)

@employee_bp.route("/<int:emp_id>", methods=["PUT"])
@login_required
def update_employee(emp_id):
    """
    PUT /employees/{id}
    - Admin: can update any field
    - Employee: can only update own profile (limited fields)
    """
    data = request.get_json(silent=True) or {}
    return EmployeeController.update_employee(emp_id, data)

@employee_bp.route("/<int:emp_id>", methods=["DELETE"])
@login_required
def delete_employee(emp_id):
    """
    DELETE /employees/{id}
    - Admin: can delete any employee except self
    - Employee: can delete own account (self-remove)
    """
    return EmployeeController.delete_employee(emp_id)
