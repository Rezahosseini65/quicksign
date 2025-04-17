import json

from django.test import TestCase
from django.urls import reverse

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

