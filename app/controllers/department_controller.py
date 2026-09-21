"""
Department Controller - app/controllers/department_controller.py
"""
import logging
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from flask import jsonify
from app import db
from app.models.department import Department
from app.models.employee import Employee

logger = logging.getLogger(__name__)

class DepartmentController:

    @staticmethod
    def get_all():
        try:
            depts = Department.query.order_by(Department.id).all()
            return jsonify({"count": len(depts), "departments": [d.to_dict() for d in depts]}), 200
        except OperationalError as e:
            return jsonify({"error": "Database unavailable", "details": str(e)}), 503
        except SQLAlchemyError as e:
            return jsonify({"error": "Database error"}), 500

    @staticmethod
    def create(data):
        name = (data.get("department_name") or "").strip()
        if not name:
            return jsonify({"error": "department_name is required"}), 400
        if len(name) < 2:
            return jsonify({"error": "department_name too short"}), 400

        if Department.query.filter_by(department_name=name).first():
            return jsonify({"error": "Department name already exists"}), 409

        manager_id = data.get("manager_id")
        if manager_id:
            try:
                manager_id = int(manager_id)
            except ValueError:
                return jsonify({"error": "manager_id must be integer"}), 400
            if not Employee.query.get(manager_id):
                return jsonify({"error": f"Employee {manager_id} not found for manager"}), 404
        else:
            manager_id = None

        try:
            dept = Department(department_name=name, manager_id=manager_id)
            db.session.add(dept)
            db.session.commit()
            return jsonify({"message": "Department created", "department": dept.to_dict()}), 201
        except IntegrityError as e:
            db.session.rollback()
            return jsonify({"error": "Integrity error", "details": str(e)}), 409
        except SQLAlchemyError as e:
            db.session.rollback()
            return jsonify({"error": "Database error", "details": str(e)}), 500

    @staticmethod
    def update(dept_id, data):
        try:
            dept = Department.query.get(dept_id)
            if not dept:
                return jsonify({"error": f"Department {dept_id} not found"}), 404

            if "department_name" in data and data["department_name"]:
                new_name = data["department_name"].strip()
                if Department.query.filter(Department.id != dept_id, Department.department_name == new_name).first():
                    return jsonify({"error": "Department name already exists"}), 409
                dept.department_name = new_name

            if "manager_id" in data:
                mid = data["manager_id"]
                if mid in [None, ""]:
                    dept.manager_id = None
                else:
                    try:
                        mid = int(mid)
                    except ValueError:
                        return jsonify({"error": "manager_id must be integer"}), 400
                    if not Employee.query.get(mid):
                        return jsonify({"error": f"Employee {mid} not found"}), 404
                    dept.manager_id = mid

            db.session.commit()
            return jsonify({"message": "Department updated", "department": dept.to_dict()}), 200
        except SQLAlchemyError as e:
            db.session.rollback()
            return jsonify({"error": "Database error", "details": str(e)}), 500

    @staticmethod
    def delete(dept_id):
        try:
            dept = Department.query.get(dept_id)
            if not dept:
                return jsonify({"error": f"Department {dept_id} not found"}), 404
            # Nullify employees' department before delete
            Employee.query.filter_by(department_id=dept_id).update({Employee.department_id: None})
            db.session.delete(dept)
            db.session.commit()
            return jsonify({"message": f"Department {dept_id} deleted"}), 200
        except SQLAlchemyError as e:
            db.session.rollback()
            return jsonify({"error": "Database error", "details": str(e)}), 500
