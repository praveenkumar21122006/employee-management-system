"""
Employee Controller - app/controllers/employee_controller.py

Business logic layer (Controller in MVC).
Handles CRUD, validation, and graceful DB error handling.
Role-aware: Admin can do all, Employee can view and edit own limited fields.
"""
import logging
from datetime import datetime
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from flask import jsonify, g

from app import db
from app.models.employee import Employee
from app.models.department import Department
from app.services.validation import validate_employee_payload
from app.services.auth import get_current_user

logger = logging.getLogger(__name__)

class EmployeeController:
    """Controller encapsulating employee operations."""

    @staticmethod
    def create_employee(data: dict):
        """Create a new employee record. Admin only (checked at route). Supports password."""
        is_valid, errors = validate_employee_payload(data, is_update=False)
        if not is_valid:
            return jsonify({"error": "Validation failed", "details": errors}), 400

        # Optional password validation
        password = data.get("password")
        if password and len(password) < 6:
            return jsonify({"error": "Validation failed", "details": {"password": "Password must be at least 6 characters"}}), 400

        # Check department exists if provided
        dept_id = data.get("department_id")
        if dept_id:
            try:
                dept_id = int(dept_id)
            except ValueError:
                return jsonify({"error": "department_id must be integer"}), 400
            if not Department.query.get(dept_id):
                return jsonify({"error": f"Department with id {dept_id} not found"}), 404

        # Check email uniqueness preemptively
        if Employee.query.filter_by(email=data["email"].strip().lower()).first():
            return jsonify({"error": "Email already exists"}), 409

        try:
            hire_date = data.get("hire_date")
            if hire_date:
                hire_date = datetime.strptime(hire_date, "%Y-%m-%d").date()
            else:
                hire_date = datetime.utcnow().date()

            emp = Employee(
                first_name=data["first_name"].strip(),
                last_name=data["last_name"].strip(),
                email=data["email"].strip().lower(),
                phone=data.get("phone"),
                hire_date=hire_date,
                department_id=dept_id,
                salary=float(data["salary"]),
                role=data["role"]
            )
            # Set password if provided, else generate a default (email prefix + 123) - but mark as needs change
            if password:
                emp.set_password(password)
            else:
                # For admin-created employees without password, set default and require change
                emp.set_password("changeme123")
            db.session.add(emp)
            db.session.commit()
            logger.info(f"Created employee {emp.id}: {emp.email}")
            return jsonify({"message": "Employee created", "employee": emp.to_dict()}), 201

        except IntegrityError as e:
            db.session.rollback()
            logger.warning(f"Integrity error on create: {e}")
            return jsonify({"error": "Database integrity error - likely duplicate email"}), 409
        except OperationalError as e:
            db.session.rollback()
            logger.error(f"DB operational error: {e}")
            return jsonify({"error": "Database unavailable", "details": str(e)}), 503
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"DB error on create: {e}")
            return jsonify({"error": "Database error", "details": str(e)}), 500
        except Exception as e:
            db.session.rollback()
            logger.exception(f"Unexpected error on create: {e}")
            return jsonify({"error": "Internal server error", "details": str(e)}), 500

    @staticmethod
    def get_all_employees(args):
        """
        Retrieve all employees with optional filters:
        - ?department=Engineering  (by department name, case-insensitive, partial match)
        - ?department_id=1
        - ?search=john  (search first_name, last_name, email)
        Requires login (checked at route). Employees see all? Yes, but salary hidden for non-admin? Keep visible but could restrict.
        """
        try:
            query = Employee.query

            # Filter by department name
            dept_name = args.get("department")
            if dept_name:
                query = query.join(Department, Employee.department_id == Department.id)\
                             .filter(Department.department_name.ilike(f"%{dept_name}%"))

            # Filter by department_id
            dept_id = args.get("department_id")
            if dept_id:
                try:
                    query = query.filter(Employee.department_id == int(dept_id))
                except ValueError:
                    return jsonify({"error": "department_id must be integer"}), 400

            # General search
            search = args.get("search")
            if search:
                like = f"%{search}%"
                query = query.filter(
                    db.or_(
                        Employee.first_name.ilike(like),
                        Employee.last_name.ilike(like),
                        Employee.email.ilike(like)
                    )
                )

            employees = query.order_by(Employee.id.desc()).all()
            # For Employee role, hide salary? Keep but maybe mask - spec says include. We'll include but frontend will hide for Employees.
            return jsonify({
                "count": len(employees),
                "employees": [e.to_dict() for e in employees]
            }), 200

        except OperationalError as e:
            logger.error(f"DB operational error on list: {e}")
            return jsonify({"error": "Database unavailable", "details": str(e)}), 503
        except SQLAlchemyError as e:
            logger.error(f"DB error on list: {e}")
            return jsonify({"error": "Database error", "details": str(e)}), 500

    @staticmethod
    def get_employee_by_id(emp_id: int):
        """Fetch single employee. Login required."""
        try:
            emp = Employee.query.get(emp_id)
            if not emp:
                return jsonify({"error": f"Employee with id {emp_id} not found"}), 404
            return jsonify({"employee": emp.to_dict()}), 200
        except OperationalError as e:
            logger.error(f"DB operational error on get: {e}")
            return jsonify({"error": "Database unavailable"}), 503
        except SQLAlchemyError as e:
            logger.error(f"DB error on get: {e}")
            return jsonify({"error": "Database error"}), 500

    @staticmethod
    def update_employee(emp_id: int, data: dict):
        """Update employee information. Role-aware."""
        current = get_current_user()
        is_admin = current and current.role == "Admin"
        is_self = current and current.id == emp_id

        # Authorization: Admin can update anyone, Employee can only update self
        if not is_admin and not is_self:
            return jsonify({"error": "Forbidden: employees can only update their own profile"}), 403

        is_valid, errors = validate_employee_payload(data, is_update=True)
        if not is_valid:
            return jsonify({"error": "Validation failed", "details": errors}), 400

        # Password validation if provided
        if "password" in data and data["password"]:
            if len(data["password"]) < 6:
                return jsonify({"error": "Validation failed", "details": {"password": "Password must be at least 6 characters"}}), 400

        try:
            emp = Employee.query.get(emp_id)
            if not emp:
                return jsonify({"error": f"Employee with id {emp_id} not found"}), 404

            # If Employee self-update, restrict fields they can change
            if not is_admin and is_self:
                # Only allow first_name, last_name, phone, email, password, hire_date
                allowed = {"first_name", "last_name", "phone", "email", "password", "hire_date"}
                # Strip disallowed fields silently
                data = {k: v for k, v in data.items() if k in allowed}
                if "email" in data and data["email"]:
                    new_email = data["email"].strip().lower()
                    if new_email != emp.email:
                        if Employee.query.filter_by(email=new_email).first():
                            return jsonify({"error": "Email already exists"}), 409
                        emp.email = new_email
                for field in ["first_name", "last_name", "phone"]:
                    if field in data and data[field] not in [None, ""]:
                        setattr(emp, field, str(data[field]).strip())
                if "hire_date" in data and data["hire_date"]:
                    emp.hire_date = datetime.strptime(data["hire_date"], "%Y-%m-%d").date()
                if "password" in data and data["password"]:
                    emp.set_password(data["password"])
                db.session.commit()
                logger.info(f"Employee self-updated {emp_id}")
                return jsonify({"message": "Profile updated", "employee": emp.to_dict()}), 200

            # Admin path - full update
            # Check email uniqueness if changing
            if "email" in data and data["email"]:
                new_email = data["email"].strip().lower()
                if new_email != emp.email:
                    if Employee.query.filter_by(email=new_email).first():
                        return jsonify({"error": "Email already exists"}), 409
                    emp.email = new_email

            if "department_id" in data:
                dept_id = data["department_id"]
                if dept_id in [None, ""]:
                    emp.department_id = None
                else:
                    try:
                        dept_id = int(dept_id)
                    except ValueError:
                        return jsonify({"error": "department_id must be integer"}), 400
                    if not Department.query.get(dept_id):
                        return jsonify({"error": f"Department {dept_id} not found"}), 404
                    emp.department_id = dept_id

            # Update other fields if provided
            for field in ["first_name", "last_name", "phone", "role"]:
                if field in data and data[field] not in [None, ""]:
                    setattr(emp, field, str(data[field]).strip())

            if "salary" in data and data["salary"] not in [None, ""]:
                emp.salary = float(data["salary"])

            if "hire_date" in data and data["hire_date"]:
                emp.hire_date = datetime.strptime(data["hire_date"], "%Y-%m-%d").date()

            if "password" in data and data["password"]:
                emp.set_password(data["password"])

            db.session.commit()
            logger.info(f"Updated employee {emp_id} by admin {current.id if current else 'unknown'}")
            return jsonify({"message": "Employee updated", "employee": emp.to_dict()}), 200

        except IntegrityError as e:
            db.session.rollback()
            return jsonify({"error": "Integrity error", "details": str(e)}), 409
        except OperationalError as e:
            db.session.rollback()
            logger.error(f"DB operational error on update: {e}")
            return jsonify({"error": "Database unavailable"}), 503
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"DB error on update: {e}")
            return jsonify({"error": "Database error"}), 500

    @staticmethod
    def delete_employee(emp_id: int):
        """
        Remove an employee record.
        - Admin: can delete any employee except self
        - Employee: can delete own account (self-remove)
        """
        try:
            emp = Employee.query.get(emp_id)
            if not emp:
                return jsonify({"error": f"Employee with id {emp_id} not found"}), 404

            current = get_current_user()
            is_admin = current and current.role == "Admin"
            is_self = current and current.id == emp_id

            # Authorization
            if not is_admin and not is_self:
                return jsonify({"error": "Forbidden: employees can only remove their own account"}), 403
            if is_admin and is_self:
                return jsonify({"error": "Admin cannot delete own account. Ask another admin."}), 400

            # If employee is a manager, nullify manager_id in departments
            Department.query.filter_by(manager_id=emp_id).update({Department.manager_id: None})

            db.session.delete(emp)
            db.session.commit()
            logger.info(f"Deleted employee {emp_id} by {'admin' if is_admin else 'self'} {current.id if current else 'unknown'}")
            # If self-delete, clear session
            if is_self:
                from flask import session
                session.clear()
            return jsonify({"message": f"Employee {emp_id} deleted successfully", "self_deleted": bool(is_self)}), 200

        except OperationalError as e:
            db.session.rollback()
            logger.error(f"DB operational error on delete: {e}")
            return jsonify({"error": "Database unavailable"}), 503
        except SQLAlchemyError as e:
            db.session.rollback()
            logger.error(f"DB error on delete: {e}")
            return jsonify({"error": "Database error"}), 500
