"""
Employee Model - app/models/employee.py

Represents Employees table:
- id (PK), first_name, last_name, email (unique), phone, hire_date, department_id (FK), salary, role, password_hash
"""
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class Employee(db.Model):
    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    hire_date = db.Column(db.Date, nullable=False, default=date.today)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    salary = db.Column(db.Float, nullable=False, default=50000)
    role = db.Column(db.String(20), nullable=False, default="Employee")  # Admin / Employee
    password_hash = db.Column(db.String(255), nullable=True)  # nullable for legacy rows, set on creation

    # Relationship to Department
    department = db.relationship(
        "Department",
        back_populates="employees",
        foreign_keys=[department_id],
        lazy="joined"
    )

    # ---- Auth helpers ----
    def set_password(self, password: str):
        """Hash and store password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify password against stored hash."""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)

    def to_dict(self, include_sensitive=False):
        """Serialize employee to dict for JSON responses."""
        data = {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "full_name": f"{self.first_name} {self.last_name}",
            "email": self.email,
            "phone": self.phone,
            "hire_date": self.hire_date.isoformat() if self.hire_date else None,
            "department_id": self.department_id,
            "department_name": self.department.department_name if self.department else None,
            "salary": self.salary,
            "role": self.role
        }
        if include_sensitive:
            data["has_password"] = bool(self.password_hash)
        return data

    def __repr__(self):
        return f"<Employee {self.first_name} {self.last_name} ({self.email})>"
