import logging

from django.contrib.auth import authenticate
from django.db import IntegrityError

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .models import CustomUser
from .throttles import PhoneCheckThrottle
from .serializers import (PhoneNumberCheckSerializer,
                          UserLoginSerializer,
                          UserRegisterSerializer,
                          UserProfileSerializer)
from quicksign.utils.services import BlockService, get_token_for_user, OTPService

# Create your views here.

logger=logging.getLogger(__name__)

class PhoneNumberCheckView(APIView):
    throttle_classes = [PhoneCheckThrottle]

    def post(self, request, *args, **kwargs):
        """
        Check the status of a user's mobile number

        This view examines the status of a mobile number and determines:
             Whether the number is currently blocked or not
             Whether the user is already registered (requires login)
             Whether the user is new (requires registration)

        """
        ip_address = request.META.get('REMOTE_ADDR')

        serializer = PhoneNumberCheckSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data["phone_number"]

        if BlockService.is_blocked(phone_number, ip_address):
            block_status = BlockService.get_block_status(phone_number, ip_address)
            remaining_minutes = block_status['block_time_left'] // 60
            return Response(
                {
                    "code": "Account_temporarily_blocked.",
                    "detail": "Account temporarily blocked due to too many attempts",
                    "remaining_time": f"{remaining_minutes} minutes"
                },
                status=status.HTTP_403_FORBIDDEN
            )

        try:
            user = CustomUser.objects.get(phone_number=phone_number)
            return Response(
                {
                    "status": "registered",
                    "phone_number": phone_number,
                    "message": f"User {phone_number} needs to login",
                    "user_id": user.id
                },
                status=status.HTTP_200_OK
            )
        except CustomUser.DoesNotExist:
            otp_response = OTPService.send_otp_code(phone_number)
            return Response(
                {
                    "status": "not_registered",
                    "phone_number": phone_number,
                    **otp_response
                },
                status=status.HTTP_404_NOT_FOUND
            )


class UserLoginView(APIView):

    def post(self, request, *args, **kwargs):
        ip_address = request.META.get('REMOTE_ADDR')

        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        phone_number = serializer.validated_data["phone_number"]
        password = serializer.validated_data["password"]

        # Check if user or IP is blocked
        if BlockService.is_blocked(phone_number, ip_address):
            block_status = BlockService.get_block_status(phone_number, ip_address)
            remaining_minutes = block_status['block_time_left'] // 60
            return Response(
                {
                    'detail': 'Account temporarily blocked due to too many attempts',
                    'remaining_time': f'{remaining_minutes} minutes'
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Attempt authentication
        user = authenticate(phone_number=phone_number, password=password)

        if not user:
            # Handle failed attempt
            attempts = BlockService.increment_attempts(phone_number, ip_address)
            remaining_attempts = 3 - attempts
            return Response(
                {
                    'detail': 'Invalid credentials',
                    'remaining_attempts': remaining_attempts,
                    'message': f'Account will be blocked after {remaining_attempts} more failed attempts' if remaining_attempts > 0 else 'Account blocked for 1 hour'
                },
                status=status.HTTP_401_UNAUTHORIZED
            )
        BlockService.reset_attempts(ip_address)

        return Response(get_token_for_user(user), status=status.HTTP_200_OK)


class UserRegisterView(APIView):
    """
    User registration endpoint with two-step validation:
    1. OTP verification
    2. Profile creation
    """
    def post(self, request, *args, **kwargs):
        ip_address = request.META.get('REMOTE_ADDR')
        # Step 1: Verify OTP
        auth_serializer = UserRegisterSerializer(data=request.data,context={"request": request})
        auth_serializer.is_valid(raise_exception=True)

        phone_number = auth_serializer.validated_data["phone_number"]

        # Step 2: Create profile
        profile_serializer = UserProfileSerializer(data=request.data,context={'phone_number': phone_number})
        profile_serializer.is_valid(raise_exception=True)

        try:
            user = CustomUser.objects.create_user(
                phone_number=phone_number,
                email=profile_serializer.validated_data["email"],
                first_name=profile_serializer.validated_data["first_name"],
                last_name=profile_serializer.validated_data["last_name"],
                password=profile_serializer.validated_data["password"]
            )

            BlockService.reset_attempts(ip_address)
            return Response(
                data=get_token_for_user(user),
                status=status.HTTP_201_CREATED
            )

        except IntegrityError as e:
            return Response(
                {
                    "code": "user_creation_failed",
                    "detail": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"User registration failed: {str(e)}")
            return Response(
                {
                    "code": "server_error",
                    "detail": "Internal server error"
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
