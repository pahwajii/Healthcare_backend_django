from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Doctor, Patient, PatientDoctorMapping


@override_settings(
    DATABASES={"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
)
class HealthcareApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="user@example.com",
            email="user@example.com",
            password="StrongPass123!",
        )
        self.client.force_authenticate(self.user)

    def test_patient_crud_is_scoped_to_authenticated_user(self):
        response = self.client.post(
            "/api/patients/",
            {"name": "Jane Doe", "age": 31, "gender": "female"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        other_user = get_user_model().objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="StrongPass123!",
        )
        Patient.objects.create(
            created_by=other_user,
            name="Private Patient",
            age=44,
            gender="male",
        )

        response = self.client.get("/api/patients/")
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Jane Doe")

    def test_mapping_requires_patient_owner(self):
        other_user = get_user_model().objects.create_user(
            username="other@example.com",
            email="other@example.com",
            password="StrongPass123!",
        )
        patient = Patient.objects.create(
            created_by=other_user,
            name="Other Patient",
            age=55,
            gender="female",
        )
        doctor = Doctor.objects.create(
            name="Dr. Singh",
            specialization="Cardiology",
            email="dr.singh@example.com",
        )

        response = self.client.post(
            "/api/mappings/",
            {"patient": patient.id, "doctor": doctor.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PatientDoctorMapping.objects.exists())
