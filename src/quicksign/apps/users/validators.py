from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


class PhoneNumberValidator(RegexValidator):
    """
    Validate Iranian mobile numbers in format '+989xxxxxxxxx' (12 digits total).
    """
    regex = r"^\+989\d{9}$"
    message = _(
        "Phone number must be entered in the format: '+989xxxxxxxxx'. Up to 12 digits allowed."
    )
    code = "phone_number_is_invalid"


phone_number_validator = PhoneNumberValidator()