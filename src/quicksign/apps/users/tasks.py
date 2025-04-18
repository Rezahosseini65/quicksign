import logging

from celery import shared_task

from .models import CustomUser

logger = logging.getLogger(__name__)

@shared_task
def send_verification_code(*, phone_number, verification_code):
    """
    Send the verification code to the user via SMS.
    """
    logger.info(f"Sending verification code {verification_code} to phone: {phone_number}")