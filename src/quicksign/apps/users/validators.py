import re

from django.core.exceptions import ValidationError
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


def number_validator(password)-> any:
    """
    Validates that password contains at least one numeric character.
    """
    regex = re.compile('[0-9]')
    if regex.search(password) is None:
        raise ValidationError(
            _("password must include number"),
            code="password_must_include_number"
        )


def letter_validator(password)-> any:
    """
    Validates that password contains at least one alphabetical character.
    """
    regex = re.compile('[a-zA-Z]')
    if regex.search(password) is None:
        raise ValidationError(
            _("password must include letter"),
            code="password_must_include_letter"
        )


phone_number_validator = PhoneNumberValidator()