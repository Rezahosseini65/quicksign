from datetime import timedelta

from django.core.cache import cache


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
        cache.set(f"failed_attempts_{phone_number}", 3, timeout=block_duration.total_seconds())

    @staticmethod
    def unblock_user(phone_number=None, ip_address=None):
        """
        Remove block from user by phone number or IP address.
        """
        if not phone_number and not ip_address:
            raise ValueError("Either phone_number or ip_address must be provided")

        cache.delete(f"phone_blocked_{phone_number}")
        cache.delete(f"ip_blocked_{ip_address}")
        cache.delete(f"failed_attempts_{phone_number}")

    @staticmethod
    def increment_attempts(phone_number, ip_address):
        """
        Increment failed attempts counter and block if exceeds limit.
        """
        attempts = cache.get(f"failed_attempts_{phone_number}", 0)
        attempts += 1
        cache.set(f"failed_attempts_{phone_number}", attempts, timeout=3600)

        if attempts >= 3:
            BlockService.block_user(phone_number, ip_address)
        return attempts

    @staticmethod
    def reset_attempts(phone_number):
        """
        Reset failed attempts counter for given phone number.
        """
        cache.delete(f"failed_attempts_{phone_number}")

    @staticmethod
    def get_block_status(phone_number=None, ip_address=None):
        """
        Get current block status including remaining attempts and block time.
        """
        is_blocked = BlockService.is_blocked(phone_number, ip_address)
        attempts = cache.get(f"failed_attempts_{phone_number}", 0) if phone_number else 0

        block_time_left = 0
        if is_blocked:
            if phone_number:
                block_time_left = cache.ttl(f"phone_blocked_{phone_number}")
            if ip_address:
                ip_time_left = cache.ttl(f"ip_blocked_{ip_address}")
                block_time_left = max(block_time_left, ip_time_left)

        return {
            'is_blocked': is_blocked,
            'remaining_attempts': max(0, 3 - attempts),
            'block_time_left': block_time_left
        }