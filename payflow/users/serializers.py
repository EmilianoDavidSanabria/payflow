from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ["email", "password"]

    def validate_email(self, value):
        email = value.strip().lower()

        if not email:
            raise serializers.ValidationError("Email is required")

        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists")

        return email

    def validate_password(self, value):
        validate_password(value)
        return value

    def create(self, validated_data):
        email = validated_data["email"]
        password = validated_data["password"]

        base_username = email.split("@")[0].strip().lower() or "user"
        username = base_username
        suffix_attempts = 0

        while User.objects.filter(username__iexact=username).exists():
            suffix_attempts += 1
            username = f"{base_username}_{uuid4().hex[:8]}"
            if suffix_attempts > 10:
                username = f"user_{uuid4().hex[:12]}"
                break

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )
        return user


class CurrentUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username", "date_joined"]
        read_only_fields = fields