"""
Attendance Routes - app/routes/attendance_routes.py

REST endpoints for attendance with timing, name, dept, role.
"""
from flask import Blueprint, request
from app.controllers.attendance_controller import AttendanceController
from app.services.auth import login_required, admin_required

attendance_bp = Blueprint("attendance", __name__, url_prefix="/api/attendance")

@attendance_bp.route("/check-in", methods=["POST"])
@login_required
def check_in():
    """
    POST /attendance/check-in
    Body: { employee_id? (admin), date? (YYYY-MM-DD, admin), check_in? (HH:MM or ISO), notes? }
    Employee: checks in self for today
    Admin: can check-in for any employee + any date
    """
    data = request.get_json(silent=True) or {}
    return AttendanceController.check_in(data)

@attendance_bp.route("/check-out", methods=["POST"])
@login_required
def check_out():
    """
    POST /attendance/check-out
    Body: { employee_id?, date?, check_out? (HH:MM or ISO), notes? }
    """
    data = request.get_json(silent=True) or {}
    return AttendanceController.check_out(data)

@attendance_bp.route("", methods=["GET"])
@login_required
def list_attendance():
    """
    GET /attendance
    Query: ?date=YYYY-MM-DD&employee_id=1&department=Engineering&status=Present&from=YYYY-MM-DD&to=YYYY-MM-DD&search=john
    Admin sees all, Employee sees own.
    """
    return AttendanceController.list_attendance(request.args)

@attendance_bp.route("/<int:att_id>", methods=["GET"])
@login_required
def get_one(att_id):
    return AttendanceController.get_one(att_id)

@attendance_bp.route("/<int:att_id>", methods=["PUT"])
@login_required
def update(att_id):
    """
    PUT /attendance/{id}
    Admin can edit all fields, Employee can edit own notes only.
    Body: { check_in, check_out, date, status, notes, employee_id }
    """
    data = request.get_json(silent=True) or {}
    return AttendanceController.update(att_id, data)

@attendance_bp.route("/<int:att_id>", methods=["DELETE"])
@login_required
def delete(att_id):
    """DELETE /attendance/{id} - Admin only (checked in controller)"""
    return AttendanceController.delete(att_id)

# Convenience: create direct record (admin)
@attendance_bp.route("/record", methods=["POST"])
@login_required
def create_record():
    """
    POST /attendance/record - Admin create arbitrary record
    Body: { employee_id*, date, check_in, check_out, status, notes }
    Implemented via check_in then check_out if both provided, or direct.
    For simplicity, use check-in flow with admin privileges.
    """
    # Use check_in logic to create, then optionally check_out
    data = request.get_json(silent=True) or {}
    if not data.get("employee_id"):
        return {"error": "employee_id required"}, 400
    # If no check_in provided, default to now
    from app.controllers.attendance_controller import AttendanceController
    res, status = AttendanceController.check_in(data)
    if status not in (200, 201) and data.get("check_out"):
        return res, status
    if data.get("check_out") and status in (200, 201):
        # Need to fetch the created id and do check-out
        # res is Flask response, parse json
        try:
            import json
            j = res.get_json()
            att = j.get("attendance")
            if att and not att.get("check_out"):
                # do check-out
                return AttendanceController.check_out(data)
        except Exception:
            pass
    return res, status
