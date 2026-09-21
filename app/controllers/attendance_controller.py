"""
Attendance Controller - app/controllers/attendance_controller.py

MVC Controller for attendance: check-in/out, list, edit, delete.
Role-aware:
- Employee: can check-in/out for self only, view own records
- Admin: can view all, check-in/out for any employee, edit/delete any
"""
import logging
from datetime import datetime, date, timedelta
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from flask import jsonify, g
from app import db
from app.models.attendance import Attendance
from app.models.employee import Employee
from app.models.department import Department
from app.services.auth import get_current_user

logger = logging.getLogger(__name__)

def _parse_date(s):
    if not s:
        return date.today()
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None

def _now():
    return datetime.now()

class AttendanceController:

    @staticmethod
    def check_in(data: dict):
        """POST /attendance/check-in - mark check-in for self or (admin) for employee_id"""
        current = get_current_user()
        if not current:
            return jsonify({"error": "Authentication required"}), 401

        is_admin = current.role == "Admin"
        # Determine target employee
        target_id = data.get("employee_id")
        if target_id:
            try:
                target_id = int(target_id)
            except ValueError:
                return jsonify({"error": "employee_id must be integer"}), 400
            if not is_admin and target_id != current.id:
                return jsonify({"error": "Employees can only check-in for themselves"}), 403
        else:
            target_id = current.id

        target = Employee.query.get(target_id)
        if not target:
            return jsonify({"error": f"Employee {target_id} not found"}), 404

        # Date handling - default today, admin can specify date
        date_str = data.get("date")
        att_date = _parse_date(date_str) if date_str else date.today()
        if att_date is None:
            return jsonify({"error": "Invalid date format, use YYYY-MM-DD"}), 400
        if not is_admin and att_date != date.today():
            return jsonify({"error": "Employees can only check-in for today"}), 403

        # Check if already checked in today
        existing = Attendance.query.filter_by(employee_id=target_id, date=att_date).first()
        now = _now()
        # Determine desired status first (admin can override)
        desired_status = data.get("status") if is_admin and data.get("status") in ["Present", "Absent", "Late", "On Leave"] else None
        # Handle Absent/On Leave without check_in (admin only)
        if desired_status in ["Absent", "On Leave"] and not data.get("check_in"):
            # Create absent record without timing
            try:
                if existing:
                    return jsonify({"error": f"Attendance already exists for {att_date}", "attendance": existing.to_dict()}), 409
                att = Attendance(
                    employee_id=target_id,
                    date=att_date,
                    check_in=None,
                    check_out=None,
                    status=desired_status,
                    notes=data.get("notes")
                )
                db.session.add(att)
                db.session.commit()
                return jsonify({"message": f"Marked {desired_status}", "attendance": att.to_dict()}), 201
            except IntegrityError as e:
                db.session.rollback()
                return jsonify({"error": "Attendance already exists for this date"}), 409

        # Allow custom check_in time for admin via payload
        custom_in = data.get("check_in")
        if custom_in:
            try:
                # accept "HH:MM" or ISO datetime
                if "T" in custom_in:
                    check_in_time = datetime.fromisoformat(custom_in)
                elif len(custom_in) == 5 and ":" in custom_in:
                    # HH:MM today
                    t = datetime.strptime(custom_in, "%H:%M").time()
                    check_in_time = datetime.combine(att_date, t)
                else:
                    check_in_time = datetime.fromisoformat(custom_in)
            except Exception:
                return jsonify({"error": "Invalid check_in format, use HH:MM or ISO datetime"}), 400
        else:
            check_in_time = now

        try:
            if existing:
                if existing.check_in:
                    return jsonify({"error": f"Already checked in at {existing.check_in.strftime('%H:%M:%S')} on {att_date}", "attendance": existing.to_dict()}), 409
                existing.check_in = check_in_time
                # Auto status: if after 09:30 mark Late
                if desired_status:
                    existing.status = desired_status
                elif check_in_time.time() > datetime.strptime("09:30", "%H:%M").time():
                    existing.status = "Late"
                else:
                    existing.status = "Present"
                db.session.commit()
                return jsonify({"message": "Checked in", "attendance": existing.to_dict()}), 200
            else:
                if desired_status:
                    status = desired_status
                else:
                    status = "Late" if check_in_time.time() > datetime.strptime("09:30", "%H:%M").time() else "Present"
                att = Attendance(
                    employee_id=target_id,
                    date=att_date,
                    check_in=check_in_time,
                    status=status,
                    notes=data.get("notes")
                )
                db.session.add(att)
                db.session.commit()
                return jsonify({"message": "Checked in", "attendance": att.to_dict()}), 201
        except IntegrityError as e:
            db.session.rollback()
            return jsonify({"error": "Attendance already exists for this date"}), 409
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"check-in error: {e}")
            return jsonify({"error": "Database error", "details": str(e)}), 500

    @staticmethod
    def check_out(data: dict):
        """POST /attendance/check-out"""
        current = get_current_user()
        if not current:
            return jsonify({"error": "Authentication required"}), 401

        is_admin = current.role == "Admin"
        target_id = data.get("employee_id")
        if target_id:
            try:
                target_id = int(target_id)
            except ValueError:
                return jsonify({"error": "employee_id must be integer"}), 400
            if not is_admin and target_id != current.id:
                return jsonify({"error": "Employees can only check-out for themselves"}), 403
        else:
            target_id = current.id

        date_str = data.get("date")
        att_date = _parse_date(date_str) if date_str else date.today()
        if att_date is None:
            return jsonify({"error": "Invalid date format"}), 400
        if not is_admin and att_date != date.today():
            return jsonify({"error": "Employees can only check-out for today"}), 403

        existing = Attendance.query.filter_by(employee_id=target_id, date=att_date).first()
        if not existing or not existing.check_in:
            return jsonify({"error": f"No check-in found for {att_date}, check-in first"}), 404
        if existing.check_out:
            return jsonify({"error": f"Already checked out at {existing.check_out.strftime('%H:%M:%S')}", "attendance": existing.to_dict()}), 409

        now = _now()
        custom_out = data.get("check_out")
        if custom_out:
            try:
                if "T" in custom_out:
                    check_out_time = datetime.fromisoformat(custom_out)
                elif len(custom_out) == 5 and ":" in custom_out:
                    t = datetime.strptime(custom_out, "%H:%M").time()
                    check_out_time = datetime.combine(att_date, t)
                else:
                    check_out_time = datetime.fromisoformat(custom_out)
            except Exception:
                return jsonify({"error": "Invalid check_out format"}), 400
        else:
            check_out_time = now

        if check_out_time <= existing.check_in:
            return jsonify({"error": "check-out must be after check-in"}), 400

        try:
            existing.check_out = check_out_time
            # Update notes if provided
            if data.get("notes"):
                existing.notes = data.get("notes")
            db.session.commit()
            return jsonify({"message": "Checked out", "attendance": existing.to_dict()}), 200
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"check-out error: {e}")
            return jsonify({"error": "Database error"}), 500

    @staticmethod
    def list_attendance(args):
        """
        GET /attendance
        Query params:
          - date=YYYY-MM-DD (filter specific date, default all)
          - employee_id
          - department (name partial)
          - status
          - from, to (date range)
          - search (name/email)
        Role:
          - Admin: sees all
          - Employee: sees own only (unless admin)
        """
        current = get_current_user()
        if not current:
            return jsonify({"error": "Authentication required"}), 401

        is_admin = current.role == "Admin"
        try:
            query = Attendance.query.join(Employee, Attendance.employee_id == Employee.id)

            # Non-admin sees only own
            if not is_admin:
                query = query.filter(Attendance.employee_id == current.id)
            else:
                # Admin can filter by employee_id
                emp_id = args.get("employee_id")
                if emp_id:
                    try:
                        query = query.filter(Attendance.employee_id == int(emp_id))
                    except ValueError:
                        return jsonify({"error": "employee_id must be integer"}), 400

                # Admin filter by department name
                dept = args.get("department")
                if dept:
                    query = query.join(Department, Employee.department_id == Department.id).filter(Department.department_name.ilike(f"%{dept}%"))

                # search name/email
                search = args.get("search")
                if search:
                    like = f"%{search}%"
                    query = query.filter(db.or_(Employee.first_name.ilike(like), Employee.last_name.ilike(like), Employee.email.ilike(like)))

            # Date filters
            date_str = args.get("date")
            if date_str:
                d = _parse_date(date_str)
                if not d:
                    return jsonify({"error": "Invalid date format"}), 400
                query = query.filter(Attendance.date == d)

            # Range
            from_str = args.get("from")
            to_str = args.get("to")
            if from_str:
                d = _parse_date(from_str)
                if not d:
                    return jsonify({"error": "Invalid from date"}), 400
                query = query.filter(Attendance.date >= d)
            if to_str:
                d = _parse_date(to_str)
                if not d:
                    return jsonify({"error": "Invalid to date"}), 400
                query = query.filter(Attendance.date <= d)

            if args.get("status"):
                query = query.filter(Attendance.status == args.get("status"))

            # Order by date desc, id desc
            records = query.order_by(Attendance.date.desc(), Attendance.id.desc()).all()
            return jsonify({"count": len(records), "attendance": [r.to_dict() for r in records]}), 200
        except OperationalError as e:
            logger.error(f"attendance list db error: {e}")
            return jsonify({"error": "Database unavailable", "details": str(e)}), 503
        except SQLAlchemyError as e:
            logger.error(f"attendance list error: {e}")
            return jsonify({"error": "Database error", "details": str(e)}), 500

    @staticmethod
    def get_one(att_id):
        current = get_current_user()
        is_admin = current.role == "Admin"
        try:
            att = Attendance.query.get(att_id)
            if not att:
                return jsonify({"error": f"Attendance {att_id} not found"}), 404
            if not is_admin and att.employee_id != current.id:
                return jsonify({"error": "Forbidden"}), 403
            return jsonify({"attendance": att.to_dict()}), 200
        except SQLAlchemyError as e:
            return jsonify({"error": "Database error"}), 500

    @staticmethod
    def update(att_id, data):
        """PUT /attendance/{id} - Admin only or self can update notes/status limited"""
        current = get_current_user()
        is_admin = current.role == "Admin"
        try:
            att = Attendance.query.get(att_id)
            if not att:
                return jsonify({"error": f"Attendance {att_id} not found"}), 404
            is_self = att.employee_id == current.id
            if not is_admin and not is_self:
                return jsonify({"error": "Forbidden"}), 403

            # Employee self can only update notes? Admin can update all
            if not is_admin and is_self:
                # Only allow notes update for self
                if "notes" in data:
                    att.notes = data["notes"]
                else:
                    return jsonify({"error": "Employees can only update notes"}), 403
                db.session.commit()
                return jsonify({"message": "Attendance updated", "attendance": att.to_dict()}), 200

            # Admin full update
            if "check_in" in data:
                if data["check_in"] in [None, ""]:
                    att.check_in = None
                else:
                    try:
                        val = data["check_in"]
                        if "T" in val:
                            att.check_in = datetime.fromisoformat(val)
                        else:
                            att.check_in = datetime.fromisoformat(val)
                    except Exception:
                        return jsonify({"error": "Invalid check_in format"}), 400
            if "check_out" in data:
                if data["check_out"] in [None, ""]:
                    att.check_out = None
                else:
                    try:
                        val = data["check_out"]
                        if "T" in val:
                            att.check_out = datetime.fromisoformat(val)
                        else:
                            att.check_out = datetime.fromisoformat(val)
                    except Exception:
                        return jsonify({"error": "Invalid check_out format"}), 400
            if "date" in data and data["date"]:
                d = _parse_date(data["date"])
                if not d:
                    return jsonify({"error": "Invalid date"}), 400
                att.date = d
            if "status" in data and data["status"] in ["Present", "Absent", "Late", "On Leave"]:
                att.status = data["status"]
            if "notes" in data:
                att.notes = data["notes"]
            if "employee_id" in data and data["employee_id"]:
                try:
                    new_emp = int(data["employee_id"])
                    if not Employee.query.get(new_emp):
                        return jsonify({"error": f"Employee {new_emp} not found"}), 404
                    att.employee_id = new_emp
                except ValueError:
                    return jsonify({"error": "employee_id must be integer"}), 400

            db.session.commit()
            return jsonify({"message": "Attendance updated", "attendance": att.to_dict()}), 200
        except IntegrityError as e:
            db.session.rollback()
            return jsonify({"error": "Integrity error (duplicate date?)"}), 409
        except SQLAlchemyError as e:
            db.session.rollback()
            return jsonify({"error": "Database error", "details": str(e)}), 500

    @staticmethod
    def delete(att_id):
        """DELETE /attendance/{id} - Admin only"""
        current = get_current_user()
        if current.role != "Admin":
            return jsonify({"error": "Admin privileges required"}), 403
        try:
            att = Attendance.query.get(att_id)
            if not att:
                return jsonify({"error": f"Attendance {att_id} not found"}), 404
            db.session.delete(att)
            db.session.commit()
            return jsonify({"message": f"Attendance {att_id} deleted"}), 200
        except SQLAlchemyError as e:
            db.session.rollback()
            return jsonify({"error": "Database error"}), 500
