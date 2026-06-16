# Interview Prep: Healthcare Backend Django Project

---

## 1. PROJECT OVERVIEW (Say this when asked "Walk me through your project")

> "This is a RESTful backend built with Django REST Framework for a healthcare application. It supports user registration and login with JWT authentication, CRUD operations for Patients and Doctors, and a many-to-many mapping between Patients and Doctors. The key design decision is that every patient is scoped to the user who created them — so doctors are global resources but patients are private per user."

---

## 2. ARCHITECTURE & DESIGN

### Models

**TimeStampedModel (Abstract Base)**
```python
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True
```
- `abstract = True` means no DB table is created for this model itself — it only adds fields to child models.
- `auto_now_add` sets the field only on creation; `auto_now` updates on every `.save()`.

**Patient**
- Linked to `settings.AUTH_USER_MODEL` via ForeignKey — uses `settings.AUTH_USER_MODEL` (not `User` directly) so it's swappable.
- `on_delete=CASCADE` means if the user is deleted, all their patients are deleted too.
- `related_name="patients"` allows `user.patients.all()` reverse lookup.

**PatientDoctorMapping**
- A through/join model representing many-to-many between Patient and Doctor.
- Has a `UniqueConstraint` on `(patient, doctor)` — prevents duplicate assignments at the DB level.
- Only supports GET, POST, DELETE (no PUT/PATCH) via `http_method_names`.

### Why not use ManyToManyField directly?
The explicit mapping model gives you:
- Timestamps on the relationship itself
- The ability to add extra fields later (e.g., `assigned_date`, `notes`)
- Explicit control over the join table

---

## 3. AUTHENTICATION (JWT)

### How JWT works here
- Uses `djangorestframework-simplejwt`
- Login returns two tokens: `access` (60 min) and `refresh` (7 days)
- Protected endpoints require `Authorization: Bearer <access_token>` header

### The Login Flow (explain step by step)
1. Client POSTs `{email, password}` to `/api/auth/login/`
2. `LoginSerializer.validate()` runs:
   - Looks up user by email (`email__iexact` for case-insensitive)
   - Calls Django's `authenticate()` with `username=user.username` (because Django auth uses `username` internally)
   - If credentials match, generates `RefreshToken` via simplejwt
3. Returns `{access, refresh, user}` in response

### Why `username=user.username` in authenticate()?
Django's default auth backend checks the `username` field, not `email`. Since we store `username=email` during registration, this works correctly.

### Settings for JWT
```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
}
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "AUTH_HEADER_TYPES": ("Bearer",),
}
```

---

## 4. VIEWS — Deep Dive

### ViewSets vs APIView vs GenericAPIView

| Class                     | Use case in this project                  |
|---------------------------|-------------------------------------------|
| `generics.CreateAPIView`  | RegisterView — only needs POST            |
| `generics.GenericAPIView` | LoginView — custom `post()` method        |
| `viewsets.ModelViewSet`   | Patient, Doctor — full CRUD automatically |

### PatientViewSet — Scoping to user
```python
def get_queryset(self):
    return Patient.objects.filter(created_by=self.request.user).order_by("-created_at")

def perform_create(self, serializer):
    serializer.save(created_by=self.request.user)
```
- `get_queryset` ensures users only see THEIR patients — security at the queryset level
- `perform_create` auto-assigns `created_by` so the client never needs to send it

**Interview Q: Why not pass `created_by` in the request body?**
Because a malicious user could pass another user's ID. By injecting it server-side in `perform_create`, we guarantee correctness.

### PatientDoctorMappingViewSet
```python
def get_queryset(self):
    return PatientDoctorMapping.objects.filter(patient__created_by=self.request.user)
        .select_related("patient", "doctor")
```
- `patient__created_by` — double underscore traverses FK relationship to check ownership
- `.select_related("patient", "doctor")` — JOIN query to avoid N+1 problem

### Custom action: `list_by_patient`
```python
def list_by_patient(self, request, pk=None):
    queryset = self.get_queryset().filter(patient_id=pk)
    serializer = self.get_serializer(queryset, many=True)
    return Response(serializer.data)
```
Wired manually in urls.py because it's a non-standard action.

---

## 5. SERIALIZERS — Deep Dive

### RegisterSerializer
```python
password = serializers.CharField(write_only=True, validators=[validate_password])
```
- `write_only=True` — password never appears in response
- `validate_password` — Django's built-in strength validator
- Custom `validate_email` normalizes to lowercase and checks uniqueness
- `create()` uses `user.set_password()` (never store plain text), sets `username=email`

### LoginSerializer
- Uses `Serializer` (not `ModelSerializer`) because it doesn't map to a single model
- `validate()` method does the authentication logic and returns tokens

### PatientDoctorMappingSerializer
```python
patient_detail = PatientSerializer(source="patient", read_only=True)
doctor_detail = DoctorSerializer(source="doctor", read_only=True)
```
- `patient` and `doctor` are writable FK fields (accept IDs on write)
- `patient_detail` and `doctor_detail` are nested read-only objects (return full data on read)
- This pattern gives you: simple write (just send IDs), rich read (get full nested objects)

### Validation in serializer vs view
The serializer validates patient ownership:
```python
def validate_patient(self, patient):
    request = self.context["request"]
    if patient.created_by != request.user:
        raise serializers.ValidationError("Patient does not belong to this user.")
    return patient
```
The view also checks it in `perform_create`. This is **defense in depth** — validated at both layers.

---

## 6. URL ROUTING

```python
router = DefaultRouter()
router.register("patients", PatientViewSet, basename="patient")
router.register("doctors", DoctorViewSet, basename="doctor")
```
The `DefaultRouter` auto-generates:
- `GET/POST /patients/` → list + create
- `GET/PUT/PATCH/DELETE /patients/<pk>/` → retrieve, update, destroy

For mappings — manually wired because of the custom `list_by_patient` action:
```python
mapping_list = PatientDoctorMappingViewSet.as_view({"get": "list", "post": "create"})
mapping_detail = PatientDoctorMappingViewSet.as_view({"get": "list_by_patient", "delete": "destroy"})
```
`GET /mappings/<pk>/` calls `list_by_patient` (lists all doctors for that patient) instead of the default `retrieve` (get one mapping by its own ID).

---

## 7. DATABASE & SETTINGS

- **PostgreSQL** configured via environment variables using `python-decouple`
- `decouple.config()` reads from `.env` file — keeps secrets out of source code
- `BigAutoField` as default PK — future-proof (won't overflow like `AutoField`)
- `USE_TZ = True` — all datetimes stored in UTC

---

## 8. TESTS

```python
@override_settings(
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
)
class HealthcareApiTests(APITestCase):
```
- `override_settings` swaps PostgreSQL for in-memory SQLite during tests — no external DB needed
- `APITestCase` provides `self.client` with DRF-aware request methods
- `force_authenticate` bypasses JWT for test simplicity

**Test 1: Patient scoping**
- Creates a patient as user A
- Creates another patient as user B directly
- Asserts user A's list only returns 1 patient (their own)

**Test 2: Mapping ownership**
- Tries to assign a patient belonging to another user
- Asserts 400 response and no mapping created

---

## 9. COMMON INTERVIEW QUESTIONS & ANSWERS

**Q: What is the N+1 problem and how do you solve it here?**
> If you loop over 10 mappings and access `mapping.patient.name` each time, Django fires 10 extra DB queries. `select_related("patient", "doctor")` in `get_queryset` performs a SQL JOIN and fetches everything in one query.

**Q: What's the difference between `select_related` and `prefetch_related`?**
> `select_related` does a SQL JOIN — works for ForeignKey/OneToOne (single object). `prefetch_related` does a separate query and Python-side joining — works for ManyToMany or reverse FK (multiple objects).

**Q: How does the UniqueConstraint prevent duplicate mappings?**
> `models.UniqueConstraint(fields=["patient", "doctor"], name="unique_patient_doctor_mapping")` adds a UNIQUE constraint at the PostgreSQL level. Even if app-level validation is bypassed, the DB will raise `IntegrityError`.

**Q: What is `auto_now_add` vs `auto_now`?**
> `auto_now_add=True` sets the datetime once when the record is created and never changes it. `auto_now=True` sets it every time `.save()` is called. You cannot manually set either field.

**Q: Why use `email__iexact` instead of `email`?**
> Case-insensitive lookup. "User@Example.com" and "user@example.com" should be treated as the same email. `iexact` does a `LOWER()` comparison in SQL.

**Q: What does `permission_classes = [permissions.AllowAny]` on register/login mean?**
> The global default requires authentication (`IsAuthenticated`), but register and login obviously can't require a token. `AllowAny` overrides the default for those specific views.

**Q: What happens if two users try to register with the same email simultaneously (race condition)?**
> The `validate_email` check in the serializer could pass for both, but the DB `UNIQUE` constraint on `email` (from Django's default User model) would cause one to fail with `IntegrityError`. In production you'd catch this and return a 400.

**Q: Why is `http_method_names` restricted on PatientDoctorMappingViewSet?**
> Mappings are binary — you either have one or you don't. There's no concept of "partially updating" a mapping. Restricting to GET/POST/DELETE prevents meaningless PUT/PATCH calls.

**Q: What is `python-decouple` and why use it over `os.environ`?**
> `python-decouple` reads from a `.env` file in development and from actual environment variables in production, with type casting and defaults. It's cleaner than raw `os.environ.get()` and separates config from code.

**Q: How would you add pagination?**
> Add to `REST_FRAMEWORK` settings:
```python
"DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
"PAGE_SIZE": 20,
```

**Q: How would you add filtering (e.g., filter patients by gender)?**
> Use `django-filter` package and add `filterset_fields = ["gender", "age"]` to the ViewSet.

**Q: How would you secure the Doctor endpoints? Currently any authenticated user can create/edit doctors.**
> Add a custom permission class checking `request.user.is_staff`, or add a role field to the User model. Could also create a separate `AdminDoctorViewSet` with `IsAdminUser` permission.

**Q: What would you change to scale this to production?**
> - Add Redis-based caching for doctor lists (they don't change often)
> - Add rate limiting on auth endpoints (prevent brute force)
> - Use `django-filter` + pagination
> - Token refresh endpoint (already built into simplejwt at `/api/token/refresh/`)
> - Add logging/monitoring middleware
> - Use gunicorn + nginx instead of dev server

---

## 10. QUICK REFERENCE: API ENDPOINTS

| Method | URL | Auth? | Description |
|---|---|---|---|
| POST | `/api/auth/register/` | No | Register user |
| POST | `/api/auth/login/` | No | Get JWT tokens |
| GET/POST | `/api/patients/` | Yes | List/create my patients |
| GET/PUT/PATCH/DELETE | `/api/patients/<id>/` | Yes | Manage one patient |
| GET/POST | `/api/doctors/` | Yes | List/create doctors |
| GET/PUT/PATCH/DELETE | `/api/doctors/<id>/` | Yes | Manage one doctor |
| GET/POST | `/api/mappings/` | Yes | List all / create mapping |
| GET | `/api/mappings/<patient_id>/` | Yes | List doctors for a patient |
| DELETE | `/api/mappings/<id>/` | Yes | Remove a mapping |

---

## 11. THINGS TO MENTION TO IMPRESS

1. **Abstract model pattern** — `TimeStampedModel` is a clean DRY approach to auditing
2. **Defense in depth** — ownership check in both serializer AND view
3. **N+1 prevention** — `select_related` in `get_queryset`
4. **Test isolation** — `@override_settings` with SQLite in-memory
5. **Secrets management** — `.env` via `python-decouple`, never hardcoded
6. **DB-level constraints** — `UniqueConstraint` as a safety net beyond app validation
7. **Nested serializer pattern** — write with IDs, read with full nested objects
