from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .serializers import PhoneNumberCheckSerializer
from .models import CustomUser
from quicksign.utils.services import BlockService

# Create your views here.


class PhoneNumberCheckView(APIView):
    def post(self, request, *args, **kwargs):
        """
        بررسی وضعیت شماره موبایل کاربر

        این ویو وضعیت شماره موبایل را بررسی می‌کند و مشخص می‌کند که:
        - آیا شماره مسدود شده است یا خیر
        آیا کاربر قبلاً ثبت‌نام کرده است (نیاز به لاگین دارد)
        - آیا کاربر جدید است (نیاز به ثبت‌نام دارد)
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
            return Response(
                {
                    "status": "not_registered",
                    "phone_number": phone_number,
                    "message": f"User {phone_number} needs to register"
                },
                status=status.HTTP_404_NOT_FOUND
            )


