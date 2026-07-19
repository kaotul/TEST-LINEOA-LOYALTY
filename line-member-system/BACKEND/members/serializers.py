from datetime import date

from rest_framework import serializers

from .models import Member


class MemberRegistrationSerializer(serializers.ModelSerializer):
    """
    Validates the form fields submitted by the LIFF app.

    Deliberately does NOT accept `line_user_id`, `display_name` or
    `picture_url` from the client -- those are set server-side from the
    verified LINE ID token, never from request body, so a user can never
    register/overwrite another user's profile.
    """

    class Meta:
        model = Member
        fields = [
            "first_name",
            "last_name",
            "phone_number",
            "email",
            "date_of_birth",
        ]

    def validate_first_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("First name is required.")
        return value

    def validate_last_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Last name is required.")
        return value

    def validate_date_of_birth(self, value):
        today = date.today()
        if value >= today:
            raise serializers.ValidationError("Date of birth must be in the past.")
        age_years = (today - value).days // 365
        if age_years > 120:
            raise serializers.ValidationError("Please check the date of birth.")
        return value


class MemberCardSerializer(serializers.ModelSerializer):
    """Read-only representation used to render the member card / Flex Message."""

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Member
        fields = [
            "member_no",
            "full_name",
            "display_name",
            "picture_url",
            "phone_number",
            "email",
            "date_of_birth",
            "created_at",
        ]

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
