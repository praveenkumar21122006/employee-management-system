"""
Auth Controller - app/controllers/auth_controller.py

Handles register / login / logout / me.
"""
import logging
from datetime import datetime
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from flask import jsonify, request, session

from app import db
from app.models.employee import Employee
from app.models.department import Department
from app.services.validation import validate_employee_payload
from app.services.auth import login_user, logout_user, get_current_user

logger = logging.getLogger(__name__)

class AuthController:

    @staticmethod
    def register(data: dict):
        """
        Public registration: creates Employee account.
        Admin can also use this to create Admins when authenticated as Admin.
        For non-admin, role is forced to Employee regardless of payload.
        """
        # Basic required fields + password
        required = ["first_name", "last_name", "email", "password", "salary"]
        errors = {}
        for f in required:
            if not data.get(f):
                errors[f] = f"{f} is required"
        if errors:
            return jsonify({"error": "Validation failed", "details": errors}), 400

        password = data.get("password", "")
        if len(password) < 6:
            return jsonify({"error": "Validation failed", "details": {"password": "Password must be at least 6 characters"}}), 400

        # Determine role first and inject for validation (public defaults to Employee)
        current = get_current_user()
        requested_role = data.get("role", "Employee")
        # Temporarily set role for validation if missing
        data_for_validation = dict(data)
        if "role" not in data_for_validation or not data_for_validation["role"]:
            data_for_validation["role"] = "Employee"

        # Reuse employee payload validation (excluding password)
        is_valid, v_errors = validate_employee_payload(data_for_validation, is_update=False)
        if not is_valid:
            return jsonify({"error": "Validation failed", "details": v_errors}), 400

        # Role handling: only admins can assign Admin role
        if current and current.role == "Admin":
            role = requested_role if requested_role in ("Admin","Employee") else "Employee"
        else:
            # Public or employee -> force Employee
            if requested_role == "Admin" and not current:
                # Block public Admin creation unless no users exist yet (first admin bootstrap)
                if Employee.query.count() > 0:
                    role = "Employee"
                else:
                    role = "Admin"  # first user can be admin
            else:
                role = "Employee"
            if requested_role == "Admin" and role == "Employee" and Employee.query.count() > 0 and not (current and current.role=="Admin"):
                # silently downgrade, but inform
                pass

        # Check email uniqueness
        email = data["email"].strip().lower()
        if Employee.query.filter_by(email=email).first():
            return jsonify({"error": "Email already exists"}), 409

        # Department check
        dept_id = data.get("department_id")
        if dept_id:
            try:
                dept_id = int(dept_id)
            except ValueError:
                return jsonify({"error": "department_id must be integer"}), 400
            if not Department.query.get(dept_id):
                return jsonify({"error": f"Department {dept_id} not found"}), 404
        else:
            dept_id = None

        # hire_date
        hire_date = data.get("hire_date")
        if hire_date:
            try:
                hire_date = datetime.strptime(hire_date, "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"error": "hire_date must be YYYY-MM-DD"}), 400
        else:
            hire_date = datetime.utcnow().date()

        try:
            emp = Employee(
                first_name=data["first_name"].strip(),
                last_name=data["last_name"].strip(),
                email=email,
                phone=data.get("phone"),
                hire_date=hire_date,
                department_id=dept_id,
                salary=float(data["salary"]),
                role=role
            )
            emp.set_password(password)
            db.session.add(emp)
            db.session.commit()
            logger.info(f"Registered {emp.email} as {emp.role}")
            # Auto-login after register? Optional: don't auto-login for admin creates
            # Only auto-login if public self-registration
            if not current:
                login_user(emp)
            return jsonify({"message": "Registered successfully", "employee": emp.to_dict(), "role_assigned": role}), 201
        except IntegrityError as e:
            db.session.rollback()
            return jsonify({"error": "Email already exists"}), 409
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"Register DB error: {e}")
            return jsonify({"error": "Database error", "details": str(e)}), 500

    @staticmethod
    def login(data: dict):
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        if not email or not password:
            return jsonify({"error": "Email and password required"}), 400

        try:
            user = Employee.query.filter_by(email=email).first()
            if not user or not user.check_password(password):
                return jsonify({"error": "Invalid email or password"}), 401
            login_user(user)
            logger.info(f"Login: {user.email}")
            return jsonify({"message": "Login successful", "employee": user.to_dict()}), 200
        except OperationalError as e:
            return jsonify({"error": "Database unavailable", "details": str(e)}), 503
        except SQLAlchemyError as e:
            logger.error(f"Login error: {e}")
            return jsonify({"error": "Database error"}), 500

    @staticmethod
    def logout():
        logout_user()
        return jsonify({"message": "Logged out"}), 200

    @staticmethod
    def me():
        user = get_current_user()
        if not user:
            return jsonify({"error": "Not authenticated"}), 401
        return jsonify({"employee": user.to_dict()}), 200
