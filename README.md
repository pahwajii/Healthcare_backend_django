# Healthcare Backend

Django REST Framework backend for a healthcare application with JWT authentication, PostgreSQL configuration, patient and doctor CRUD APIs, and patient-doctor assignments.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Update `.env` with your PostgreSQL credentials, then run:

```powershell
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

## API

Use `Authorization: Bearer <access_token>` for protected endpoints.

| Method | Endpoint | Description |
| --- | --- | --- |
| POST | `/api/auth/register/` | Register with `name`, `email`, `password` |
| POST | `/api/auth/login/` | Login with `email` and `password` |
| POST/GET | `/api/patients/` | Create/list authenticated user's patients |
| GET/PUT/DELETE | `/api/patients/<id>/` | Manage one owned patient |
| POST/GET | `/api/doctors/` | Create/list doctors |
| GET/PUT/DELETE | `/api/doctors/<id>/` | Manage one doctor |
| POST/GET | `/api/mappings/` | Assign/list patient-doctor mappings |
| GET | `/api/mappings/<patient_id>/` | List doctors assigned to a patient |
| DELETE | `/api/mappings/<id>/` | Remove a mapping |

Example login payload:

```json
{
  "email": "user@example.com",
  "password": "StrongPass123!"
}
```
