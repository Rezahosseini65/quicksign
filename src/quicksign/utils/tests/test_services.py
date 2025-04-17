from unittest.mock import patch, MagicMock

from django.test import TestCase
from django.core.cache import cache

from quicksign.utils.services import BlockService, OTPService
from quicksign.apps.users.tasks import send_verification_code



class BlockServiceTestCase(TestCase):
    def setUp(self):
        self.phone_number = '+989123456789'
        self.ip_address = '192.168.1.1'
        cache.clear()

    def test_is_blocked_with_phone(self):
        """
        Test checking block status by phone number
        """
        self.assertFalse(BlockService.is_blocked(phone_number=self.phone_number))
        BlockService.block_user(phone_number=self.phone_number)
        self.assertTrue(BlockService.is_blocked(phone_number=self.phone_number))

    def test_is_blocked_with_ip(self):
        """
        Test checking block status by IP address
        """
        self.assertFalse(BlockService.is_blocked(ip_address=self.ip_address))
        BlockService.block_user(ip_address=self.ip_address)
        self.assertTrue(BlockService.is_blocked(ip_address=self.ip_address))

    def test_block_user(self):
        """
        Test blocking user by phone and IP
        """
        BlockService.block_user(phone_number=self.phone_number, ip_address=self.ip_address)

        self.assertTrue(cache.get(f"phone_blocked_{self.phone_number}"))
        self.assertTrue(cache.get(f"ip_blocked_{self.ip_address}"))
        self.assertEqual(cache.get(f"failed_attempts_{self.phone_number}"), 3)

    def test_unblock_user(self):
        """Test unblocking user"""
        BlockService.block_user(phone_number=self.phone_number, ip_address=self.ip_address)
        BlockService.unblock_user(phone_number=self.phone_number, ip_address=self.ip_address)

        self.assertIsNone(cache.get(f"phone_blocked_{self.phone_number}"))
        self.assertIsNone(cache.get(f"ip_blocked_{self.ip_address}"))
        self.assertIsNone(cache.get(f"failed_attempts_{self.phone_number}"))

    def test_increment_attempts(self):
        """Test incrementing failed attempts"""
        attempts = BlockService.increment_attempts(self.phone_number, self.ip_address)
        self.assertEqual(attempts, 1)
        self.assertEqual(cache.get(f"failed_attempts_{self.phone_number}"), 1)

        # Test auto-block after 3 attempts
        BlockService.increment_attempts(self.phone_number, self.ip_address)
        BlockService.increment_attempts(self.phone_number, self.ip_address)
        self.assertTrue(BlockService.is_blocked(phone_number=self.phone_number))

    def test_reset_attempts(self):
        """Test resetting failed attempts"""
        BlockService.increment_attempts(self.phone_number, self.ip_address)
        BlockService.reset_attempts(self.phone_number)
        self.assertIsNone(cache.get(f"failed_attempts_{self.phone_number}"))

    def test_get_block_status(self):
        """Test getting block status information"""
        status = BlockService.get_block_status(phone_number=self.phone_number)
        self.assertEqual(status, {
            'is_blocked': False,
            'remaining_attempts': 3,
            'block_time_left': 0
        })

        BlockService.block_user(phone_number=self.phone_number)
        status = BlockService.get_block_status(phone_number=self.phone_number)
        self.assertTrue(status['is_blocked'])
        self.assertGreater(status['block_time_left'], 0)

    def test_validation_errors(self):
        """Test validation for required phone or IP"""
        with self.assertRaises(ValueError):
            BlockService.is_blocked()

        with self.assertRaises(ValueError):
            BlockService.block_user()

        with self.assertRaises(ValueError):
            BlockService.unblock_user()

    def tearDown(self):
        cache.clear()


class OTPServiceTestCase(TestCase):
    def setUp(self):
        self.phone_number = "+989123456789"
        self.valid_code = "123456"
        cache.clear()

    def tearDown(self):
        cache.clear()

    @patch("secrets.randbelow")
    def test_generate_code(self, mock_randbelow):
        """تست تولید کد و ذخیره آن در کش"""
        mock_randbelow.return_value = 23456
        code = OTPService.generate_code(self.phone_number)

        self.assertEqual(code, "123456")
        self.assertEqual(cache.get(f"verification_code_{self.phone_number}"), "123456")

    @patch("quicksign.apps.users.tasks.send_verification_code.delay")
    def test_send_otp_code(self, mock_send_verification):
        """تست ارسال کد OTP"""
        mock_send_verification.return_value = None
        result = OTPService.send_otp_code(self.phone_number)

        self.assertEqual(result["data"]["status"], "success")
        self.assertIn(self.phone_number, result["data"]["message"])
        mock_send_verification.assert_called_once_with(
            phone_number=self.phone_number,
            verification_code=cache.get(f"verification_code_{self.phone_number}")
        )

    def test_validate_code_correct(self):
        """تست صحت سنجی کد صحیح"""
        cache.set(f"verification_code_{self.phone_number}", self.valid_code, timeout=120)

        is_valid = OTPService.validate_code(self.phone_number, self.valid_code)
        print(cache.get(f"verification_code_{self.phone_number}"))
        self.assertTrue(is_valid)
        self.assertIsNone(cache.get(f"verification_code_{self.phone_number}"))

    def test_validate_code_incorrect(self):
        """تست صحت سنجی کد نادرست"""
        cache.set(f"verification_code_{self.phone_number}", self.valid_code, timeout=120)

        is_valid = OTPService.validate_code(self.phone_number, "654321")

        self.assertFalse(is_valid)

    @patch("quicksign.utils.services.logger.info")
    def test_validate_code_redis_error(self, mock_logger):
        """تست خطای ردیس در هنگام صحت سنجی"""
        with patch("django.core.cache.cache.get", side_effect=Exception("Redis Error")):
            is_valid = OTPService.validate_code(self.phone_number, self.valid_code)

            self.assertFalse(is_valid)
            mock_logger.assert_called_once_with("Redis Error: Redis Error")


