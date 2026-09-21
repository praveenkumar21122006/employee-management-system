"""
Validation Service - app/services/validation.py

Centralized validation logic for security & data integrity.
"""
import re
from datetime import datetime

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
PHONE_REGEX = re.compile(r"^[\d\s\-\+\(\)]{7,20}$")
VALID_ROLES = {"Admin", "Employee"}

def validate_email(email: str) -> tuple[bool, str]:
    if not email or not EMAIL_REGEX.match(email.strip()):
        return False, "Invalid email format. Example: name@company.com"
    return True, ""

def validate_salary(salary) -> tuple[bool, str]:
    try:
        val = float(salary)
        if val <= 0:
            return False, "Salary must be a positive number."
        if val > 10_000_000:
            return False, "Salary exceeds reasonable limit."
        return True, ""
    except (ValueError, TypeError):
        return False, "Salary must be a numeric value."

def validate_role(role: str) -> tuple[bool, str]:
    if role not in VALID_ROLES:
        return False, f"Role must be one of: {', '.join(VALID_ROLES)}"
    return True, ""

def validate_employee_payload(data: dict, is_update: bool = False) -> tuple[bool, dict]:
    """
    Validate employee creation/update payload.
    Returns (is_valid, errors_dict)
    """
    errors = {}

    # Required fields for creation
    required = ["first_name", "last_name", "email", "salary", "role"]
    if not is_update:
        for field in required:
            if field not in data or data[field] in [None, ""]:
                errors[field] = f"{field} is required."

    # Field-wise validation if present
    if "email" in data and data["email"]:
        ok, msg = validate_email(data["email"])
        if not ok:
            errors["email"] = msg

    if "salary" in data and data["salary"] not in [None, ""]:
        ok, msg = validate_salary(data["salary"])
        if not ok:
            errors["salary"] = msg

    if "role" in data and data["role"]:
        ok, msg = validate_role(data["role"])
        if not ok:
            errors["role"] = msg

    if "phone" in data and data["phone"]:
        if not PHONE_REGEX.match(str(data["phone"])):
            errors["phone"] = "Invalid phone format."

    if "hire_date" in data and data["hire_date"]:
        try:
            # Accept ISO date string YYYY-MM-DD
            datetime.strptime(str(data["hire_date"]), "%Y-%m-%d")
        except ValueError:
            errors["hire_date"] = "hire_date must be YYYY-MM-DD."

    if "first_name" in data and data["first_name"]:
        if len(str(data["first_name"]).strip()) < 2:
            errors["first_name"] = "first_name must be at least 2 characters."

    if "last_name" in data and data["last_name"]:
        if len(str(data["last_name"]).strip()) < 2:
            errors["last_name"] = "last_name must be at least 2 characters."

    return (len(errors) == 0), errors
