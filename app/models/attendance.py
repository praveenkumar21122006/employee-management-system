"""
Attendance Model - app/models/attendance.py

Tracks employee attendance with timing.

Table: attendance
- id (PK)
- employee_id (FK -> employees.id)
- date (Date, indexed)
- check_in (DateTime, nullable)
- check_out (DateTime, nullable)
- status (Present/Absent/Late/On Leave)
- hours (Float, computed as (check_out - check_in).total_seconds()/3600)
- notes (String)

Unique constraint: one record per employee per date (employee_id + date)
"""
from datetime import datetime, date
from app import db

class Attendance(db.Model):
    __tablename__ = "attendance"
    __table_args__ = (
        db.UniqueConstraint('employee_id', 'date', name='uq_employee_date'),
        db.Index('idx_attendance_date', 'date'),
        db.Index('idx_attendance_employee', 'employee_id'),
    )

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    check_in = db.Column(db.DateTime, nullable=True)
    check_out = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default="Present")  # Present / Absent / Late / On Leave
    notes = db.Column(db.String(255), nullable=True)

    # Relationship
    employee = db.relationship("Employee", backref=db.backref("attendances", lazy="dynamic", cascade="all, delete-orphan"), lazy="joined")

    @property
    def hours(self):
        if self.check_in and self.check_out:
            delta = self.check_out - self.check_in
            # handle overnight? if check_out < check_in, assume next day
            if delta.total_seconds() < 0:
                return 0
            return round(delta.total_seconds() / 3600, 2)
        return None

    @property
    def timing_display(self):
        """Human readable timing e.g. 09:00 - 17:30 (8.5h)"""
        if self.check_in and self.check_out:
            return f"{self.check_in.strftime('%H:%M')} - {self.check_out.strftime('%H:%M')} ({self.hours}h)"
        elif self.check_in:
            return f"{self.check_in.strftime('%H:%M')} - -- (checked in)"
        else:
            return "--"

    def to_dict(self):
        """Serialize with employee denormalized fields for UI (name, dept, role)"""
        emp = self.employee
        return {
            "id": self.id,
            "employee_id": self.employee_id,
            # denormalized for easy table display as requested: name, dept, role
            "employee_name": f"{emp.first_name} {emp.last_name}" if emp else "Unknown",
            "first_name": emp.first_name if emp else None,
            "last_name": emp.last_name if emp else None,
            "email": emp.email if emp else None,
            "department_id": emp.department_id if emp else None,
            "department_name": emp.department.department_name if emp and emp.department else None,
            "role": emp.role if emp else None,
            # timing fields
            "date": self.date.isoformat() if self.date else None,
            "check_in": self.check_in.isoformat() if self.check_in else None,
            "check_in_time": self.check_in.strftime("%H:%M:%S") if self.check_in else None,
            "check_out": self.check_out.isoformat() if self.check_out else None,
            "check_out_time": self.check_out.strftime("%H:%M:%S") if self.check_out else None,
            "timing": self.timing_display,
            "hours": self.hours,
            "status": self.status,
            "notes": self.notes
        }

    def __repr__(self):
        return f"<Attendance emp={self.employee_id} date={self.date} {self.status}>"
