"""
Department Model - app/models/department.py

Represents Departments table:
- id (PK), department_name, manager_id (FK -> employees.id)
"""
from app import db

class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    department_name = db.Column(db.String(100), unique=True, nullable=False)
    # manager_id references employees.id - nullable to avoid circular dependency on creation
    manager_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    # employees in this department (reverse of Employee.department)
    employees = db.relationship(
        "Employee",
        back_populates="department",
        foreign_keys="Employee.department_id",
        lazy="dynamic",
    )
    # manager relationship (one employee who manages dept)
    manager = db.relationship(
        "Employee",
        foreign_keys=[manager_id],
        post_update=True,  # needed due to circular FK
        uselist=False
    )

    def to_dict(self):
        return {
            "id": self.id,
            "department_name": self.department_name,
            "manager_id": self.manager_id,
            "manager_name": f"{self.manager.first_name} {self.manager.last_name}" if self.manager else None,
            "employee_count": self.employees.count() if self.employees else 0
        }

    def __repr__(self):
        return f"<Department {self.department_name}>"
