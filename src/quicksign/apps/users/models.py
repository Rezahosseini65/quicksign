import logging

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils.translation import gettext_lazy as _

from .validators import phone_number_validator

logger = logging.getLogger(__name__)

# Create your models here.


class UserManager(BaseUserManager):
    """
    Custom user manager for handling user creation with phone number as primary identifier
    """
    def create_user(self, phone_number, password=None, **extra_fields):
        """
        Create and return a regular user with a phone number and password.
        """
        try:
            if not phone_number:
                raise ValueError('The phone number must be set')
            user = self.model(phone_number=phone_number, **extra_fields)
            user.set_password(password)
            user.save(using=self._db)
            logger.info(f"User{phone_number} created successfully")
            return user

        except Exception as e:
            logger.error(f"User creation failed: {str(e)}")
            raise

    def create_superuser(self, phone_number, password=None, **extra_fields):
        """
        Create and save a superuser with admin privileges.
        """
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("The superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("The superuser must have is_superuser=True."))

        return self.create_user(phone_number, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model that uses phone number as the primary identifier instead of username.

    Inherits from Django's AbstractBaseUser and PermissionsMixin to provide core
    authentication functionality and permission handling.
    """
    phone_number = models.CharField(
        _("phone number"),
        max_length=13,
        unique=True,
        validators=[phone_number_validator]
    )
    email = models.EmailField(
        _("email"),
        unique=True,
        error_messages={
            "unique": _("A user with that email already exists."),
        }
    )
    first_name = models.CharField(_("first name"), max_length=128)
    last_name = models.CharField(_("last name"), max_length=128)

    is_staff = models.BooleanField(_("is_staff"), default=False)
    is_active = models.BooleanField(_("is_active"), default=True)

    created_at = models.DateTimeField(_("created"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated"), auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["email", "first_name", "last_name"]

    def __str__(self):
        return self.phone_number

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'



