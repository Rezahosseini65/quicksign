import json
from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse
from django.core.cache import cache

from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework import status

from .models import CustomUser
from .serializers import PhoneNumberCheckSerializer
from .views import PhoneNumberCheckView
from quicksign.utils.services import BlockService

# Create your tests here.


class CustomUserTestCase(TestCase):

    def setUp(self):
        self.user = CustomUser.objects.create_user(
            phone_number='+989123456789',
            email='test@example.com',
            first_name='test',
            last_name='user',
            password='testPass123'
        )

    def test_create_user(self):
        self.assertEqual(self.user.phone_number, '+989123456789')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.first_name, 'test')
        self.assertEqual(self.user.last_name, 'user')
        self.assertTrue(self.user.check_password('testPass123'))
        self.assertFalse(self.user.is_staff)
        self.assertTrue(self.user.is_active)
        self.assertIsNotNone(self.user.created_at)
        self.assertIsNotNone(self.user.updated_at)

    def test_create_superuser(self):
        """Test creating a superuser"""
        superuser = CustomUser.objects.create_superuser(
            phone_number='+989987654321',
            email='admin@example.com',
            first_name='Admin',
            last_name='User',
            password='adminPass123'
        )
        self.assertTrue(superuser.is_staff)
        self.assertTrue(superuser.is_superuser)
        self.assertTrue(superuser.is_active)

    def test_create_user_without_phone_number(self):
        """Test creating user without phone number raises error"""
        with self.assertRaises(ValueError):
            CustomUser.objects.create_user(
                phone_number='',
                email='test@example.com',
                first_name='John',
                last_name='Doe',
                password='testpass123'
            )

    def test_create_user_with_duplicate_phone_number(self):
        """Test duplicate phone numbers are not allowed"""
        with self.assertRaises(Exception):
            CustomUser.objects.create_user(
                phone_number='+989123456789',
                email='test1@example.com',
                first_name='test',
                last_name='user',
                password='testPass123'
            )

    def test_create_user_with_duplicate_email(self):
        """Test duplicate email are not allowed"""
        with self.assertRaises(Exception):
            CustomUser.objects.create_user(
                phone_number='+989123456788',
                email='test@example.com',
                first_name='test',
                last_name='user',
                password='testPass123'
            )

class PhoneNumberCheckSerializerTest(TestCase):
    def setUp(self):
        self.valid_phone = "+989123456789"
        self.invalid_phone = "09123456789"  # Missing +
        self.long_phone = "+9891234567890"  # Too long

    def test_valid_phone_number(self):
        serializer = PhoneNumberCheckSerializer(data={'phone_number': self.valid_phone})
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['phone_number'], self.valid_phone)

    def test_invalid_phone_number_format(self):
        serializer = PhoneNumberCheckSerializer(data={'phone_number': self.invalid_phone})
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone_number', serializer.errors)

    def test_long_phone_number(self):
        serializer = PhoneNumberCheckSerializer(data={'phone_number': self.long_phone})
        self.assertFalse(serializer.is_valid())
        self.assertIn('phone_number', serializer.errors)


class PhoneNumberCheckViewTest(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.blocked_phone = "+989987654321"
        self.registered_phone = "+989111111111"
        self.url = reverse('check-phone')

        # Create a registered user
        CustomUser.objects.create(phone_number=self.registered_phone)

        # Mock block service
        self.original_is_blocked = BlockService.is_blocked
        self.original_get_status = BlockService.get_block_status
        BlockService.is_blocked = lambda phone, ip: phone == self.blocked_phone
        BlockService.get_block_status = lambda phone, ip: {'block_time_left': 300}

    def tearDown(self):
        # Restore original block service methods
        BlockService.is_blocked = self.original_is_blocked
        BlockService.get_block_status = self.original_get_status

    def test_registered_user(self):
        data = {'phone_number': self.registered_phone}
        request = self.factory.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        response = PhoneNumberCheckView.as_view()(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'registered')
        self.assertEqual(response.data['phone_number'], self.registered_phone)

    def test_blocked_user(self):
        data = {'phone_number': self.blocked_phone}
        request = self.factory.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        response = PhoneNumberCheckView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['code'], 'Account_temporarily_blocked.')

    def test_invalid_phone_format(self):
        data = {'phone_number': 'invalid-format'}
        request = self.factory.post(
            self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        response = PhoneNumberCheckView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_missing_phone_number(self):
        request = self.factory.post(
            self.url,
            {},
            content_type='application/json'
        )
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        response = PhoneNumberCheckView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_number', response.data)


class BlockServiceIntegrationTest(TestCase):
    def setUp(self):
        self.phone = "+989123456789"
        self.ip = "192.168.1.1"

    def test_block_service_integration(self):
        # Test actual block service integration
        is_blocked = BlockService.is_blocked(self.phone, self.ip)
        self.assertIsInstance(is_blocked, bool)


class UserLoginViewTests(APITestCase):
    def setUp(self):
        self.login_url = reverse('login-user')
        self.user = CustomUser.objects.create_user(
            phone_number='+989123456789',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

        # Sample valid data
        self.valid_data = {
            'phone_number': '+989123456789',
            'password': 'testpass123'
        }

        # Sample invalid data
        self.invalid_password_data = {
            'phone_number': '+989123456789',
            'password': 'wrongpass'
        }

        self.invalid_phone_data = {
            'phone_number': '+989000000000',
            'password': 'testpass123'
        }

    def tearDown(self):
        cache.clear()

    def test_successful_login(self):
        """Test successful login returns tokens"""
        response = self.client.post(self.login_url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_invalid_credentials(self):
        """Test login with wrong password"""
        response = self.client.post(self.login_url, self.invalid_password_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail'], 'Invalid credentials')
        self.assertEqual(response.data['remaining_attempts'], 2)

    def test_nonexistent_user(self):
        """Test login with non-existent phone number"""
        response = self.client.post(self.login_url, self.invalid_phone_data)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.data['detail'], 'Invalid credentials')

    def test_block_after_multiple_attempts(self):
        """Test account gets blocked after 3 failed attempts"""
        for i in range(3):
            remaining = 2 - i
            response = self.client.post(self.login_url, self.invalid_password_data)
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
            if remaining > 0:
                self.assertIn(f'Account will be blocked after {remaining} more failed attempts',
                              response.data['message'])
            else:
                self.assertIn('Account blocked for 1 hour', response.data['message'])

        # Fourth attempt should be blocked
        response = self.client.post(self.login_url, self.invalid_password_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn('Account temporarily blocked due to too many attempts',
                      response.data['detail'])

    def test_block_reset_after_successful_login(self):
        """Test failed attempts counter resets after successful login"""
        # First failed attempt
        self.client.post(self.login_url, self.invalid_password_data)

        # Then successful login
        response = self.client.post(self.login_url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Failed attempts should be reset
        response = self.client.post(self.login_url, self.invalid_password_data)
        self.assertEqual(response.data['remaining_attempts'], 2)

    def test_invalid_serializer_data(self):
        """Test login with invalid phone number format"""
        invalid_data = {
            'phone_number': 'invalid-phone',
            'password': 'testpass123'
        }
        response = self.client.post(self.login_url, invalid_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('phone_number', response.data)

    @patch('quicksign.utils.services.BlockService.is_blocked', return_value=True)
    @patch('quicksign.utils.services.BlockService.get_block_status',
           return_value={'block_time_left': 1800})  # 30 minutes
    def test_blocked_user_login(self, mock_get_status, mock_is_blocked):
        """Test blocked user can't login"""
        response = self.client.post(self.login_url, self.valid_data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['remaining_time'], '30 minutes')
