# Django Interview Prep Guide - Healthcare Backend

---

## 1. 🐍 **Python Virtual Environment - क्यों जरूरी है?**

### What is it?
A **virtual environment** is an isolated Python workspace for your project. It has its own Python interpreter and installed packages separate from your system Python.

### Why use it?
```
System Python (Global)
├── Package A v1.0
├── Package B v2.0
└── Package C v1.5

Your Project venv (Isolated)
├── Package A v3.0  ← Different version!
├── Package B v2.0
└── Django 5.2 ← Only this project uses it
```

### Your Project Example:
```powershell
.venv\Scripts\Activate.ps1  # Activate venv

# Now when you run: pip install -r requirements.txt
# Packages install ONLY in .venv folder, not globally
```

### Interview Q: "What happens if you don't use virtual environments?"
**Answer:** "Different projects need different package versions. Without venv, Project A (Django 4.0) and Project B (Django 5.2) will conflict. Virtual env isolates each project completely. Also, when deploying to production, venv ensures the exact same packages run everywhere."

---

## 2. ⚙️ **manage.py - Project Management Script**

### What is it?
`manage.py` is Django's command-line utility for administrative tasks. It's auto-generated when you create a Django project.

### Common Commands in Your Project:
```bash
# Run database migrations (updates schema)
python manage.py migrate

# Create database changes from model modifications
python manage.py makemigrations

# Start development server
python manage.py runserver

# Create superuser for admin panel
python manage.py createsuperuser

# Run tests
python manage.py test

# Run custom management commands
python manage.py custom_command
```

### Your Project Structure:
```
healthcare_backend/settings.py  ← manage.py reads this
api/models.py                   ← manage.py inspects these
manage.py                       ← The main entry point
```

### Interview Q: "What happens when you run `python manage.py migrate`?"
**Answer:** "Django reads `api/migrations/` folder, checks which migrations haven't been applied yet, and executes them against the database. It updates the schema. For example, `0001_initial.py` creates Patient, Doctor, PatientDoctorMapping tables."

---

## 3. 👁️ **Views - Request Handler Logic**

### What is it?
Views contain the **business logic** for handling API requests. They receive HTTP requests and return responses.

### Your Project Views:

#### **RegisterView** - User Registration
```python
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]  # No auth needed
```
**What happens:**
1. Client POSTs `{name, email, password}`
2. Django calls `RegisterView.post()`
3. `RegisterSerializer.create()` hashes password & saves to database
4. Returns `{id, name, email}`

#### **LoginView** - Authentication
```python
class LoginView(generics.GenericAPIView):
    serializer_class = LoginSerializer
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(serializer.validated_data)  # Returns {access, refresh, user}
```

#### **PatientViewSet** - Full CRUD Operations
```python
class PatientViewSet(viewsets.ModelViewSet):
    # Automatically generates:
    # GET    /api/patients/        → list()
    # POST   /api/patients/        → create()
    # GET    /api/patients/1/      → retrieve()
    # PUT    /api/patients/1/      → update()
    # DELETE /api/patients/1/      → destroy()

    def get_queryset(self):
        # SECURITY: Each user only sees their own patients
        return Patient.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        # Auto-assign current user (prevent malicious ID passing)
        serializer.save(created_by=self.request.user)
```

### Interview Q: "Explain the difference between generics.CreateAPIView, GenericAPIView, and ViewSet"
**Answer:** 
- **CreateAPIView** - Only POST. You provide `serializer_class`. Used for RegisterView.
- **GenericAPIView** - Base for custom views. You define `post()`, `get()` etc. Used for LoginView (custom logic).
- **ViewSet** - Full CRUD automatically. One class generates 5 endpoints (list, create, retrieve, update, destroy).

---

## 4. 📋 **Serializers - Data Schema & Validation**

### What is it?
Serializers convert **Python objects ↔ JSON** and **validate** incoming data.

```
JSON (from client)
     ↓
Serializer.is_valid()  ← Validates against schema
     ↓
Python dict
     ↓
Model.save()  ← Saves to database
     ↓
Serializer(instance)  ← Converts back to JSON
     ↓
JSON (to client)
```

### Your Project Serializers:

#### **RegisterSerializer** - Validates & Creates User
```python
class RegisterSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "name", "email", "password"]

    def validate_email(self, value):
        # Custom validation: email must be unique
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("User with this email exists")
        return value

    def create(self, validated_data):
        # Custom creation logic
        user = User(
            username=validated_data["email"],
            email=validated_data["email"]
        )
        user.set_password(validated_data["password"])  # Hash password!
        user.save()
        return user
```

**What happens:**
```
Client sends: {"name": "John", "email": "john@test.com", "password": "123"}
                ↓
Serializer validates:
- email format? ✓
- unique email? ✓
- password strong? ✓ (validate_password checks)
                ↓
create() method runs:
- Hashes password with user.set_password()
- Saves to database
                ↓
Returns: {"id": 1, "name": "John", "email": "john@test.com"}
```

#### **PatientSerializer** - Patient CRUD Schema
```python
class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = ["id", "name", "age", "gender", "phone", "address", "medical_history", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]  # Client can't set these
```

**Validation automatically includes:**
- `age` must be PositiveSmallIntegerField (0-32767)
- `name` max 120 chars
- `gender` max 20 chars
- If you send extra fields → error

#### **LoginSerializer** - Validates Credentials
```python
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].lower().strip()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password")

        # Check if password matches
        user = authenticate(username=user.username, password=attrs["password"])
        if user is None:
            raise serializers.ValidationError("Invalid email or password")

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {"id": user.id, "email": user.email}
        }
```

### Interview Q: "Why use serializers instead of saving JSON directly?"
**Answer:** "Serializers provide validation, schema enforcement, and conversion. If someone sends `{age: 'abc'}`, serializer catches it before hitting database. Also, they handle nested objects, many-to-many relationships, and custom validation rules."

---

## 5. 🗂️ **Models - Database Schema Definition**

### What is it?
Models define the **database schema** using Python classes. Each model = one database table.

### Your Project Models:

#### **TimeStampedModel** - Abstract Base
```python
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)  # Set only at creation
    updated_at = models.DateTimeField(auto_now=True)      # Updates every .save()

    class Meta:
        abstract = True  # NOT a table itself, just for inheritance
```
**Why?** DRY principle - all models need timestamps. Instead of copying this code 3 times, inherit it.

#### **Patient Model** - User-Scoped Data
```python
class Patient(TimeStampedModel):
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,  # Links to Django's User model
        on_delete=models.CASCADE,   # If user deleted, delete their patients too
        related_name="patients"      # Reverse: user.patients.all()
    )
    name = models.CharField(max_length=120)
    age = models.PositiveSmallIntegerField()  # 0-32767
    gender = models.CharField(max_length=20)
    phone = models.CharField(max_length=20, blank=True)  # Optional
    address = models.TextField(blank=True)
    medical_history = models.TextField(blank=True)

    def __str__(self):
        return self.name  # Used in admin panel
```

**Generated SQL:**
```sql
CREATE TABLE api_patient (
    id BIGINT PRIMARY KEY,
    created_by_id INT REFERENCES auth_user(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    age SMALLINT NOT NULL,
    gender VARCHAR(20) NOT NULL,
    phone VARCHAR(20),
    address TEXT,
    medical_history TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

#### **Doctor Model** - Global Resource
```python
class Doctor(TimeStampedModel):
    name = models.CharField(max_length=120)
    specialization = models.CharField(max_length=120)
    email = models.EmailField(unique=True)  # Constraint at DB level
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.name} ({self.specialization})"
```

#### **PatientDoctorMapping** - Many-to-Many Join Table
```python
class PatientDoctorMapping(TimeStampedModel):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="doctor_mappings"  # patient.doctor_mappings.all()
    )
    doctor = models.ForeignKey(
        Doctor,
        on_delete=models.CASCADE,
        related_name="patient_mappings"  # doctor.patient_mappings.all()
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["patient", "doctor"],
                name="unique_patient_doctor_mapping"
            )
        ]  # Can't assign same doctor twice to same patient

    def __str__(self):
        return f"{self.patient} -> {self.doctor}"
```

### Interview Q: "Why not use ManyToManyField directly instead of an explicit mapping model?"
**Answer:** "ManyToManyField is a shortcut when the join table is just an association. But our mapping model has timestamps on the relationship, and later we might add fields like 'assigned_date', 'notes', 'status'. An explicit model gives us control over the join table."

---

## 6. 🔄 **Migrations - Why Django Needs Them?**

### What is it?
Migrations are **versioned database schema changes**. Each migration is a file that transforms the database from one state to another.

```
Initial State: No tables
     ↓ (0001_initial.py)
State 1: Patient, Doctor, PatientDoctorMapping tables
     ↓ (0002_add_field.py - hypothetical)
State 2: Added 'notes' field to Doctor
```

### Your Project Migrations:
```
api/migrations/
├── __init__.py
└── 0001_initial.py  ← Creates Patient, Doctor, PatientDoctorMapping tables
```

### Why Migrations?
**Without migrations:**
```python
# Developer 1: "I'll just run this SQL"
DROP TABLE patients;
CREATE TABLE patients (id INT, ...);

# Developer 2: "Wait, that table has data!"
# Disaster! Data lost!
```

**With migrations:**
```
python manage.py makemigrations  # Detects model changes
python manage.py migrate          # Applies in order (0001, 0002, ...)
                                  # Safe, reversible, version controlled
```

### Workflow:
```bash
# 1. Modify a model
# Edit api/models.py: add a new field

# 2. Create migration
python manage.py makemigrations
# Generates: 0002_patient_add_ssn.py

# 3. Apply migration
python manage.py migrate
# Runs: ALTER TABLE api_patient ADD COLUMN ssn VARCHAR(11);

# 4. Undo migration (if needed)
python manage.py migrate api 0001
# Rolls back to initial state
```

### Your Initial Migration (0001_initial.py) Does:
```python
CreateModel(name='Patient', fields=[...]),
CreateModel(name='Doctor', fields=[...]),
CreateModel(name='PatientDoctorMapping', fields=[...]),
AddConstraint(model='PatientDoctorMapping', constraint=UniqueConstraint(...))
```

### Interview Q: "Why is `python manage.py migrate` needed even if you have schema in models.py?"
**Answer:** "Models.py defines Python classes, not the actual database. Migrations translate those models into SQL and track changes over time. Without running migrate, no tables exist in the database. Also, migrations are version-controlled and reversible - you can see exactly what changed and when."

---

## 7. 🌐 **URLs - API Route Definition**

### What is it?
URLs map HTTP requests to views. They're the **routing system**.

```
GET /api/patients/1/
         ↓
urls.py looks up the pattern
         ↓
Finds: router.register("patients", PatientViewSet, basename="patient")
         ↓
Routes to: PatientViewSet.retrieve(pk=1)
         ↓
View queries: Patient.objects.get(id=1)
         ↓
Returns: {"id": 1, "name": "Alice", ...}
```

### Your Project URLs:

#### **api/urls.py**
```python
from django.urls import path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
# Register viewsets → Auto-generates 5 routes per viewset
router.register("patients", PatientViewSet, basename="patient")
# Generates: /api/patients/, /api/patients/<id>/

router.register("doctors", DoctorViewSet, basename="doctor")
# Generates: /api/doctors/, /api/doctors/<id>/

# Manual routes for mappings (custom logic)
mapping_list = PatientDoctorMappingViewSet.as_view({
    "get": "list",
    "post": "create"
})
mapping_detail = PatientDoctorMappingViewSet.as_view({
    "get": "list_by_patient",
    "delete": "destroy"
})

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("mappings/", mapping_list, name="mapping-list"),
    path("mappings/<int:pk>/", mapping_detail, name="mapping-detail"),
    *router.urls,  # Include all router routes
]
```

#### **healthcare_backend/urls.py** (Main URL config)
```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),  # Includes all api.urls patterns
]
```

### Generated Routes:
```
GET    /api/auth/register/          → RegisterView.post()
POST   /api/auth/login/             → LoginView.post()

GET    /api/patients/               → PatientViewSet.list()
POST   /api/patients/               → PatientViewSet.create()
GET    /api/patients/<id>/          → PatientViewSet.retrieve()
PUT    /api/patients/<id>/          → PatientViewSet.update()
DELETE /api/patients/<id>/          → PatientViewSet.destroy()

GET    /api/doctors/                → DoctorViewSet.list()
... (same 5 routes)

GET    /api/mappings/               → PatientDoctorMappingViewSet.list()
POST   /api/mappings/               → PatientDoctorMappingViewSet.create()
GET    /api/mappings/<id>/          → PatientDoctorMappingViewSet.list_by_patient()
DELETE /api/mappings/<id>/          → PatientDoctorMappingViewSet.destroy()
```

### Interview Q: "Why use routers instead of manually defining all paths?"
**Answer:** "Routers automatically generate all CRUD routes from a single registration. For PatientViewSet, it creates list, create, retrieve, update, destroy in one line. This follows DRY (Don't Repeat Yourself) and REST conventions."

---

## 8. 🔧 **Django - What is it?**

### What is it?
Django is a **full-featured web framework** for building web applications in Python.

### Architecture: MTV (Model-Template-View)
```
Client Request
     ↓
URL Router (urls.py) - "Which view handles this?"
     ↓
View (views.py) - "Get data from model, process it"
     ↓
Model (models.py) - "Query/update database"
     ↓
Database
     ↓
(Response back)
     ↓
Serializer (serializers.py) - "Convert Python object to JSON"
     ↓
Template/Response - "Return to client"
```

### Django vs Other Frameworks:
| Aspect | Django | Flask | FastAPI |
|--------|--------|-------|---------|
| Size | **Full-featured** (ORM, auth, admin, migrations) | **Lightweight** (you add everything) | **Modern** (async, fast validation) |
| Learning Curve | **Medium** (many concepts) | **Easy** (minimal setup) | **Medium** (async concepts) |
| Project Size | **Large projects** | Small-medium projects | **High-performance APIs** |
| Admin Panel | **Built-in** ✓ | Need to build | Need to build |
| ORM | **Django ORM** | SQLAlchemy (optional) | SQLAlchemy |

### Your Project Uses:
- **Django ORM** - Query database without SQL
- **Django REST Framework** - REST API utilities
- **Django Admin** - Built-in admin panel (no code needed!)
- **Django Auth** - User authentication system
- **Django Migrations** - Database versioning

### Interview Q: "Why use Django instead of FastAPI?"
**Answer:** "Django is more feature-complete. It includes ORM, authentication, admin panel, migrations - all built-in. FastAPI is faster and more modern but requires you to add libraries for everything. For a healthcare application, Django's batteries-included approach is safer."

---

## 9. 🔌 **WSGI - Web Server Gateway Interface**

### What is it?
WSGI is a **Python standard** that defines how web servers communicate with Python applications.

```
Client Request
     ↓
Web Server (Nginx, Apache)
     ↓
WSGI Server (Gunicorn, uWSGI)
     ↓
WSGI Application (healthcare_backend/wsgi.py)
     ↓
Django Application
```

### Your Project WSGI:
```python
# healthcare_backend/wsgi.py
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'healthcare_backend.settings')

application = get_wsgi_application()
```

**What happens:**
1. Web server calls `application(environ, start_response)`
2. Django processes the request
3. Returns HTTP response
4. Web server sends to client

### In Development:
```bash
python manage.py runserver
# Uses Django's development WSGI server (not for production!)
```

### In Production:
```bash
gunicorn healthcare_backend.wsgi:application
# Uses Gunicorn (production-ready WSGI server)
```

### Interview Q: "What's the difference between development and production servers?"
**Answer:** "Development server (django runserver) is single-threaded, reloads code on save, and shows errors. It's NOT safe for production. Production uses Gunicorn - multi-process, handles concurrent requests, doesn't auto-reload, logs errors safely."

---

## 10. ⚡ **ASGI - Asynchronous Server Gateway Interface**

### What is it?
ASGI is the **async version of WSGI**. It supports WebSockets and async views.

```
WSGI: Synchronous (requests blocked until response)
Request A ━━━━━━━━━━━━━━━━━━ Response A
Request B ━━━━━━━━━━━━━━━━━━ Response B

ASGI: Asynchronous (multiple concurrent connections)
Request A ━━━━━━━━ Response A
Request B ━━━━━━━━ Response B
Request C ━━━ Response C (ASGI handles all concurrently)
```

### Your Project ASGI:
```python
# healthcare_backend/asgi.py
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'healthcare_backend.settings')

application = get_asgi_application()
```

### When to Use ASGI?
- **WebSocket** - Real-time chat, notifications
- **Long-running requests** - Large file upload/download
- **Concurrent tasks** - Many simultaneous connections

### Your Project:
Your healthcare app doesn't have WebSockets yet, so WSGI is fine. If you add real-time patient notifications, you'd switch to ASGI with **Daphne** or **Uvicorn**.

### Interview Q: "When would you use ASGI over WSGI in your project?"
**Answer:** "Currently, our API is synchronous REST - WSGI is perfect. But if we add real-time features like 'doctor is typing a prescription' or 'appointment reminder notifications', we'd need ASGI with WebSockets to maintain persistent connections."

---

## 11. 🔐 **Authentication Library - djangorestframework-simplejwt**

### What is it?
Authentication = "Verify who you are". JWT (JSON Web Tokens) is a standard for stateless authentication.

### Without JWT:
```
Client: "Login as john@example.com, password: 123"
     ↓
Server: "OK! Session ID: abc123"
     ↓
Server stores in memory/database: {abc123: john's data}
     ↓
Client sends: "Session ID: abc123, get my patients"
     ↓
Server: "Looks up session, returns patients"
     ↓
Problem: If server restarts, session lost!
```

### With JWT:
```
Client: "Login as john@example.com, password: 123"
     ↓
Server: "OK! Here's JWT: eyJhbGc..."
     ↓
JWT contains: {user_id: 5, exp: 2026-06-16T20:00:00}
     ↓
Server DOESN'T store it!
     ↓
Client sends: "Authorization: Bearer eyJhbGc..."
     ↓
Server: "Verifies JWT signature, extracts user_id: 5, returns his patients"
     ↓
Advantage: Stateless! Scales to millions of users!
```

### Your Project Setup:
```python
# healthcare_backend/settings.py
INSTALLED_APPS = [
    'rest_framework',
    'rest_framework_simplejwt',  # JWT library
    'api',
]

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),      # Expires in 1 hour
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),         # Refresh expires in 7 days
    "AUTH_HEADER_TYPES": ("Bearer",),                    # Use "Bearer" prefix
}
```

### JWT Flow in Your Project:
```
1. Client POSTs to /api/auth/login/ with email + password

2. Server runs LoginSerializer.validate():
   - Looks up user by email
   - Checks password with authenticate()
   - If valid, generates RefreshToken

3. RefreshToken automatically creates:
   - access_token (short-lived, 60 min)
   - refresh_token (long-lived, 7 days)

4. Server returns:
   {
     "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
     "user": {id: 1, email: "john@..."}
   }

5. Client stores access_token in localStorage/sessionStorage

6. Client sends with every request:
   Authorization: Bearer <access_token>

7. Server validates JWT:
   - Checks signature (only server knows secret key)
   - Checks expiration (exp > now?)
   - Extracts user_id
   - Sets request.user = User(id=user_id)

8. View checks: @permission_classes([IsAuthenticated])
   - Denies if no token
   - Proceeds if valid token
```

### What's Inside a JWT?
```
Header: {alg: "HS256", typ: "JWT"}
Payload: {user_id: 5, exp: 1234567890, iat: 1234567890}
Signature: HMACSHA256(header.payload, SECRET_KEY)

Full JWT: eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjo1LCJleHAiOjEyMzQ1Njc4OTB9.signature...
```

### Interview Q: "Why use JWT instead of session tokens?"
**Answer:** "JWT is stateless - the server doesn't store anything. Session tokens require server-side storage (database/Redis). With JWT, you can scale horizontally (100 servers) without syncing sessions. Also, JWT includes claims (user_id, expiration) directly in the token, so no lookup needed."

### Interview Q: "What happens when access token expires?"
**Answer:** "Client gets 401 Unauthorized. Client then uses refresh_token to request a new access_token at `/api/token/refresh/`. Refresh tokens last 7 days. After that, user must login again."

---

## 12. 🎛️ **Admin Panel - Built-in Management Interface**

### What is it?
Django automatically generates an admin interface for all models. No code needed!

### Access It:
```bash
python manage.py createsuperuser
# Prompts for: email, password

# Then visit: http://127.0.0.1:8000/admin/
# Login with superuser credentials
```

### Your Project Admin Capabilities (Without Code):
```
- Add/Edit/Delete Patients
- Add/Edit/Delete Doctors
- Add/Edit/Delete PatientDoctorMappings
- Filters by created_at, updated_at
- Search by name, email
- Bulk delete
- Export data
```

### Customizing Admin (Optional):
```python
# api/admin.py
from django.contrib import admin
from .models import Patient, Doctor, PatientDoctorMapping

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['name', 'age', 'created_by', 'created_at']
    list_filter = ['gender', 'created_at']
    search_fields = ['name', 'medical_history']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['name', 'specialization', 'email']
    search_fields = ['name', 'specialization', 'email']

@admin.register(PatientDoctorMapping)
class PatientDoctorMappingAdmin(admin.ModelAdmin):
    list_display = ['patient', 'doctor', 'created_at']
```

### Interview Q: "What's the benefit of the admin panel?"
**Answer:** "It's a CRUD interface auto-generated from models. In production, admins can manage data without API calls. It's like Postman but visual, and built-in. Also useful for debugging - check if data is correct in database."

---

## 13. 🔑 **JWT vs Other Auth Methods**

### Why JWT is Better Than Alternatives:

#### **Basic Auth (Username:Password in every request)**
```
Client: GET /api/patients/ with Authorization: Basic dXNlcjpwYXNz
Problem: Password sent with EVERY request! Risky!
```

#### **Session-Based Auth (Django default)**
```
Client: Login, get session_id
Server: Stores {session_id: user_data} in database/Redis
Problem: Doesn't scale! 10K concurrent users = 10K server-side objects
```

#### **JWT (Your Project)**
```
Client: Login, get JWT
Server: No storage! JWT itself contains user info + signature
Advantage: Scales infinitely! Stateless! Secure!
```

### Your Project Uses JWT Because:
- **Scalable** - No session database needed
- **Mobile-friendly** - Works with React, Android, iOS
- **Microservices-ready** - Tokens work across services
- **Secure** - Signature prevents tampering

---

## 14. 👤 **User Model - Already Built-In**

### What is it?
Django provides a built-in `User` model in `django.contrib.auth`. You don't need to create it!

```python
# django.contrib.auth.models.User (Already exists!)
class User(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    password = models.CharField(max_length=128)  # Hashed!
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)  # Can access admin?
    is_superuser = models.BooleanField(default=False)  # Super admin?
    date_joined = models.DateTimeField(auto_now_add=True)
```

### Your Project Uses It:
```python
# In Patient model
created_by = models.ForeignKey(
    settings.AUTH_USER_MODEL,  # Reference to built-in User
    on_delete=models.CASCADE,
    related_name="patients"
)
```

### In RegisterView:
```python
def create(self, validated_data):
    user = User(
        username=email,
        email=email,
        first_name=first_name,
        last_name=last_name
    )
    user.set_password(password)  # Hashes password using PBKDF2
    user.save()
    return user
```

### Why Not Create Custom User Model?
**You COULD:**
```python
class CustomUser(models.Model):
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
```

**But WHY NOT:**
- Django's User is battle-tested, secure (password hashing)
- Already integrated with Django admin
- Permissions system built-in
- Migration tools assume it

### Interview Q: "Why use Django's built-in User model instead of custom?"
**Answer:** "Django's User model is secure - it hashes passwords with PBKDF2, integrates with admin panel, and has a permissions system. Creating a custom model would mean reimplementing all of this. We use `settings.AUTH_USER_MODEL` as a reference so it's swappable if needed."

---

## 🎯 **Interview Scenario Practice**

### **Interviewer**: "Walk me through what happens when someone logs in to your app"

**Your Answer:**
"When a user logs in:

1. Client POSTs email + password to `/api/auth/login/`
2. Django's URL router matches it to `LoginView`
3. `LoginSerializer.validate()` runs:
   - Looks up user by email (case-insensitive)
   - Calls Django's `authenticate()` to check password
   - If valid, generates JWT tokens via `RefreshToken.for_user()`
4. Server returns `{access_token, refresh_token, user_info}`
5. Client stores `access_token` in localStorage
6. For subsequent requests, client sends: `Authorization: Bearer <token>`
7. Django's JWT authentication middleware:
   - Extracts token from header
   - Verifies signature (only server knows SECRET_KEY)
   - Checks expiration
   - Sets `request.user` to the User object
8. View checks `@permission_classes([IsAuthenticated])`
9. If valid, view proceeds. If expired/invalid, returns 401."

---

### **Interviewer**: "Explain your database schema"

**Your Answer:**
"We have 4 tables (ignoring Django's built-ins):

1. **Patient** - User-scoped patient records
   - Foreign Key to User (created_by)
   - Fields: name, age, gender, phone, address, medical_history
   - ON DELETE CASCADE - if user deleted, patients deleted too

2. **Doctor** - Global doctors
   - Fields: name, specialization, email (unique), phone
   - No user scope - doctors visible to all users

3. **PatientDoctorMapping** - Many-to-many join table
   - Foreign Keys to Patient and Doctor
   - Unique constraint: (patient, doctor) must be unique
   - Timestamps on the relationship itself
   - Why explicit model? We might add fields later (assigned_date, notes, status)

4. **User** - Django's built-in
   - Django provides this
   - We store username=email for convenience"

---

### **Interviewer**: "How do you prevent users from seeing other users' data?"

**Your Answer:**
"It's handled at 3 levels:

1. **Model level**: Patient has `created_by` ForeignKey
2. **Queryset level**: In `PatientViewSet.get_queryset()`:
   ```python
   return Patient.objects.filter(created_by=self.request.user)
   ```
   This ensures each user only sees their own patients
3. **Serializer level**: In `PatientDoctorMappingSerializer.validate_patient()`:
   ```python
   if patient.created_by != request.user:
       raise PermissionDenied('Patient not yours')
   ```
   This prevents assigning doctors to other users' patients

Why 3 levels? Defense in depth. If one fails, others catch it."

---

## 📚 **Key Formulas to Remember**

### Django Request Flow
```
Request → URL Router → View → Model → Serializer → Response
```

### JWT Token Lifecycle
```
Login → Access Token (60 min) → Refresh Token (7 days) → Re-login
```

### Database Cascade
```
Delete User → Delete Patient (ON DELETE CASCADE) → Delete Mappings (ON DELETE CASCADE)
```

### Serializer Validation
```
JSON Input → Serializer.is_valid() → Custom validators → Model instance → model.save()
```

---

Good luck with your interview tomorrow! 🚀

