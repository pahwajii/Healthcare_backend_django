from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    DoctorViewSet,
    LoginView,
    PatientDoctorMappingViewSet,
    PatientViewSet,
    RegisterView,
)


router = DefaultRouter()
router.register("patients", PatientViewSet, basename="patient")
router.register("doctors", DoctorViewSet, basename="doctor")

mapping_list = PatientDoctorMappingViewSet.as_view({"get": "list", "post": "create"})
mapping_detail = PatientDoctorMappingViewSet.as_view(
    {"get": "list_by_patient", "delete": "destroy"}
)

urlpatterns = [
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("mappings/", mapping_list, name="mapping-list"),
    path("mappings/<int:pk>/", mapping_detail, name="mapping-detail"),
    *router.urls,
]
