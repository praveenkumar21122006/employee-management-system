# Employee Management System (EMS)

Modular, production-ready EMS built with **Python Flask + SQLite** following **MVC** architecture.

## Features

**Database Schema**
- `employees`: id (PK), first_name, last_name, email (unique), phone, hire_date, department_id (FK), salary, role (Admin/Employee)
- `departments`: id (PK), department_name (unique), manager_id (FK → employees.id)

**API Endpoints**
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/employees` | Create employee |
| GET | `/employees` | List all + filter `?department=Eng` `?department_id=1` `?search=john` |
| GET | `/employees/{id}` | Fetch single |
| PUT | `/employees/{id}` | Update |
| DELETE | `/employees/{id}` | Delete |
| GET | `/departments` | List departments |
| POST | `/departments` | Create department |
| GET | `/health` | DB health check |
| GET | `/` | Dashboard UI |

**Validation & Security**
- Email regex validation
- Salary > 0, numeric
- Role whitelist (Admin/Employee)
- Graceful `OperationalError` handling (503, no crash), `pool_pre_ping`, rollback on `IntegrityError`
- Parameterized ORM queries (no raw SQL injection)

**UI**
- Minimal responsive dashboard at `/` with search, department filter, stats, and Add/Edit/Delete modals (Tailwind CDN + vanilla JS).

---

## Architecture

```
app/
  __init__.py          # Application factory, DB init, error handlers
  config.py            # Env-based config
  models/              # M — SQLAlchemy models
    employee.py
    department.py
  controllers/         # C — Business logic
    employee_controller.py
    department_controller.py
  services/            # Validation
    validation.py
  routes/              # V/Router — Blueprints
    employee_routes.py
    department_routes.py
    view_routes.py
  views/
    templates/dashboard.html
run.py                 # Entry point
ems.db                 # SQLite (auto-created)
```

MVC flow: `Route (View)` → `Controller` → `Model` → `DB` → JSON response.

---

## Installation & Run (Local)

### Prerequisites
- Python 3.10+
- pip

### Steps
```bash
# 1. Clone / navigate
cd employee-management

# 2. Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate         # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
python run.py
# or
FLASK_ENV=development python run.py

# 5. Open
# Dashboard: http://localhost:5000/
# API:       http://localhost:5000/employees
# Health:    http://localhost:5000/health
```

**Production** with gunicorn:
```bash
gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app('production')"
```

Environment variables (optional):
```bash
export SECRET_KEY="your-secret"
export DATABASE_URL="sqlite:///ems.db"   # or postgres://...
export PORT=5000
export FLASK_ENV=production
```

---

## API Usage Examples

### Create Employee
```bash
curl -X POST http://localhost:5000/employees \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Alice",
    "last_name": "Smith",
    "email": "alice.smith@company.com",
    "phone": "+1 555-0100",
    "hire_date": "2024-03-01",
    "department_id": 1,
    "salary": 85000,
    "role": "Employee"
  }'
```

### List with Filter
```bash
curl "http://localhost:5000/employees?department=Engineering"
curl "http://localhost:5000/employees?search=alice"
curl "http://localhost:5000/employees?department_id=1"
```

### Get Single
```bash
curl http://localhost:5000/employees/1
```

### Update
```bash
curl -X PUT http://localhost:5000/employees/1 \
  -H "Content-Type: application/json" \
  -d '{"salary": 90000, "role": "Admin"}'
```

### Delete
```bash
curl -X DELETE http://localhost:5000/employees/1
```

### Departments
```bash
curl http://localhost:5000/departments
curl -X POST http://localhost:5000/departments -H "Content-Type: application/json" -d '{"department_name":"Sales"}'
```

All endpoints return JSON and proper HTTP codes: `200`, `201`, `400` (validation), `404`, `409` (duplicate), `503` (DB down).

---

## Validation Rules

- `email`: regex `^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$`
- `salary`: float > 0, ≤ 10M
- `role`: `Admin` or `Employee`
- `first_name`/`last_name`: ≥2 chars
- `phone`: optional, 7–20 chars digits/`+ - ( )`
- `hire_date`: `YYYY-MM-DD` or defaults to today

---

## Testing Graceful DB Errors

Disconnect scenario: the app catches `OperationalError` at startup and per-request, returning `503` JSON instead of crashing. Test by temporarily renaming `ems.db` or setting invalid `DATABASE_URL`.

---

## Extending

- Swap SQLite for Postgres: set `DATABASE_URL=postgresql://user:pass@host/db`
- Add auth: wrap blueprints with `flask-jwt-extended`
- Pagination: add `?page&limit` in `get_all_employees`

---

## License
MIT
