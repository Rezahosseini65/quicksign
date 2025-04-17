from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from .validators import phone_number_validator

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