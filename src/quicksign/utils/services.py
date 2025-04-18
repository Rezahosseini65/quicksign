import logging
import secrets
from datetime import timedelta

from django.core.cache import cache

from rest_framework_simplejwt.tokens import RefreshToken

from redis.lock import Lock

from quicksign.apps.users.tasks import send_verification_code

logger = logging.getLogger(__name__)

def get_token_for_user(user):
    """
    Generate JWT refresh and access tokens for a given user.
    """
    refresh = RefreshToken.for_user(user)
    return {
        "refresh":str(refresh),
        "access":str(refresh.access_token)
    }

class BlockService:
    """
    Service for managing user blocking functionality using Django cache.
    """
    @staticmethod
    def is_blocked(phone_number=None, ip_address=None):
        """
        Check if user is blocked by phone number or IP address.
        """
        if not phone_number and not ip_address:
            raise ValueError("Either phone_number or ip_address must be provided")

        if cache.get(f"phone_blocked_{phone_number}") or cache.get(f"ip_blocked_{ip_address}"):
            return True
        return False

    @staticmethod
    def block_user(phone_number=None, ip_address=None):
        """
        Block user by phone number or IP address for 1 hour.
        """
        if not phone_number and not ip_address:
            raise ValueError("Either phone_number or ip_address must be provided")

        block_duration = timedelta(hours=1)
        cache.set(f"phone_blocked_{phone_number}", True, timeout=block_duration.total_seconds())
        cache.set(f"ip_blocked_{ip_address}", True, timeout=block_duration.total_seconds())
        cache.set(f"failed_attempts_{ip_address}", 3, timeout=block_duration.total_seconds())

    @staticmethod
    def unblock_user(phone_number=None, ip_address=None):
        """
        Remove block from user by phone number or IP address.
        """
        if not phone_number and not ip_address:
            raise ValueError("Either phone_number or ip_address must be provided")

        cache.delete(f"phone_blocked_{phone_number}")
        cache.delete(f"ip_blocked_{ip_address}")
        cache.delete(f"failed_attempts_{ip_address}")

    @staticmethod
    def increment_attempts(phone_number, ip_address):
        """
        Increment failed attempts counter and block if exceeds limit.
        """
        attempts = cache.get(f"failed_attempts_{ip_address}", 0)
        attempts += 1

        cache.set(f"failed_attempts_{ip_address}", attempts, timeout=3600)

        if attempts >= 3:
            BlockService.block_user(phone_number, ip_address)
        return attempts

    @staticmethod
    def reset_attempts(ip_address):
        """
        Reset failed attempts counter for given phone number.
        """
        cache.delete(f"failed_attempts_{ip_address}")

    @staticmethod
    def get_block_status(phone_number=None, ip_address=None):
        """
        Get current block status including remaining attempts and block time.
        """
        is_blocked = BlockService.is_blocked(phone_number, ip_address)
        attempts = cache.get(f"failed_attempts_{ip_address}", 0)
        block_time_left = 0

        if is_blocked:
            if phone_number:
                block_time_left = cache.ttl(f"phone_blocked_{phone_number}")
            if ip_address:
                ip_time_left = cache.ttl(f"ip_blocked_{ip_address}")
                block_time_left = max(block_time_left, ip_time_left)

        return {
            'is_blocked': is_blocked,
            'remaining_attempts': max(0, (3 - attempts)),
            'block_time_left': block_time_left
        }


class OTPService:

    @staticmethod
    def generate_code(phone_number):
        """
        Generate a random 6-digit verification code.
        Replace this with your actual code generation logic.
        """
        code = str(secrets.randbelow(900000) + 100000)
        cache.set(
            key = f"verification_code_{phone_number}",
            value=code,
            timeout=120
        )
        return code

    @staticmethod
    def send_otp_code(phone_number):
        """
        Sends OTP code to user.
        """
        verification_code = OTPService.generate_code(phone_number)
        send_verification_code.delay(phone_number=phone_number, verification_code=verification_code )
        return {
            "data": {
                "message": f"Verification code sent to your {phone_number}",
                "retry_after": 60
            }
        }

    @staticmethod
    def validate_code(phone_number, code):
        """
        Validates a verification code for a user by checking Redis.

        Args:
            phone_number (str): The user's unique ID.
            code (str): The code to validate.

        Returns:
            bool: True if the code matches and is valid, False otherwise.

        Exceptions:
            Handles Redis errors and logs them.
        """
        try:
            redis_client = cache.client.get_client()

            look = Lock(
                redis_client,
                name=f"otp_lock_{phone_number}",
                timeout=5
            )

            with look:
                stored_code = cache.get(f"verification_code_{phone_number}")
                if stored_code == code:
                    return True
                return False

        except Exception as e:
            logger.info(f"Redis Error: {str(e)}")
            return False