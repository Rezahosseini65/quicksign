from django.core.validators import EmailValidator, MinLengthValidator
from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .models import CustomUser
from .validators import phone_number_validator, number_validator, letter_validator
from quicksign.utils.services import BlockService, OTPService

class PhoneNumberCheckSerializer(serializers.Serializer):
    phone_number = serializers.CharField(
        required=True,
        max_length=13,
        validators=[phone_number_validator]
    )

    def validate_phone_number(self, value: str)-> str:
        try:
            phone_number_validator(value)
            return value
        except ValidationError as e:
            raise serializers.ValidationError(
                "Phone number must be entered in the format: '+989xxxxxxxxx'. Up to 12 digits allowed."
            )


class UserLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(
        required=True,
        max_length=13,
        validators=[phone_number_validator],
        help_text=_("Please provide the phone number that was sent to you.")
    )
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_phone_number(self, value: str)-> str:
        try:
            phone_number_validator(value)
            return value
        except ValidationError as e:
            raise serializers.ValidationError(
                "Phone number must be entered in the format: '+989xxxxxxxxx'. Up to 12 digits allowed."
            )


class UserRegisterSerializer(serializers.Serializer):
    code = serializers.CharField(required=True, min_length=6, max_length=6)
    phone_number = serializers.CharField(
        required=True,
        max_length=13,
        validators=[phone_number_validator],
        help_text=_("Please provide the phone number that was sent to you.")
    )

    def validate(self, attrs: dict) -> dict:
        request = self.context.get("request")
        ip_address = request.META.get('REMOTE_ADDR')
        phone_number = attrs["phone_number"]

        block_status = BlockService.get_block_status(phone_number, ip_address)
        if block_status["is_blocked"]:
            raise serializers.ValidationError(
                {
                    "code": "account_blocked",
                    "detail": "Account temporarily blocked.",
                    "remaining_time": f"{block_status['block_time_left'] // 60} minutes"
                }
            )

        if not OTPService.validate_code(phone_number, attrs["code"]):
            attempts = BlockService.increment_attempts(phone_number, ip_address)
            remaining_attempts = 3 - attempts
            new_status = BlockService.get_block_status(phone_number, ip_address)
            raise serializers.ValidationError(
                {
                    "code": "invalid_otp",
                    "detail": "Invalid verification code.",
                    "remaining_attempts": new_status['remaining_attempts'],
                    'message': f'Account will be blocked after {remaining_attempts} more failed attempts'
                    if remaining_attempts > 0 else 'Account blocked for 1 hour'
                }
            )

        return attrs


class UserProfileSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[
            number_validator,
            letter_validator,
            MinLengthValidator(limit_value=8, message="Password must be at least 8 characters long.")
        ]
    )
    confirm_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = ['email', 'first_name', 'last_name', 'password', 'confirm_password']
        extra_kwargs = {
            'email': {
                'validators': [EmailValidator()],
                'error_messages': {'unique': 'A user with that email already exists.'}
            }
        }

    def validate_email(self, value: str) -> str:
        if CustomUser.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already exists")
        return value

    def validate(self, attrs: dict) -> dict:
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                "confirm_password": "Passwords do not match"
            })
        attrs.pop('confirm_password', None)
        return attrs