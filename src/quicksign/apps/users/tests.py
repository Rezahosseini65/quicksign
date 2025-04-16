from django.test import TestCase

from .models import CustomUser

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

