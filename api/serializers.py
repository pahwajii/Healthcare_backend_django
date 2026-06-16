from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Doctor, Patient, PatientDoctorMapping


User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    name = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = User
        fields = ["id", "name", "email", "password"]
        read_only_fields = ["id"]

    def validate_email(self, value):
        email = value.lower().strip()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def create(self, validated_data):
        name = validated_data.pop("name").strip()
        email = validated_data.pop("email")
        first_name, _, last_name = name.partition(" ")
        user = User(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )
        user.set_password(validated_data["password"])
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].lower().strip()
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("Invalid email or password.") from exc

        user = authenticate(
            request=self.context.get("request"),
            username=user.username,
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")

        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": user.id,
                "name": user.get_full_name(),
                "email": user.email,
            },
        }


class PatientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Patient
        fields = [
            "id",
            "name",
            "age",
            "gender",
            "phone",
            "address",
            "medical_history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = [
            "id",
            "name",
            "specialization",
            "email",
            "phone",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class PatientDoctorMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientDoctorMapping
        fields = [
            "id",
            "patient",
            "doctor",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def validate_patient(self, patient):
        request = self.context["request"]
        if patient.created_by != request.user:
            raise serializers.ValidationError("Patient does not belong to this user.")
        return patient
