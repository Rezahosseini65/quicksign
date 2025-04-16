from django.contrib import admin

from .models import CustomUser

# Register your models here.


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('phone_number', 'email', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_active', 'created_at', 'updated_at')
    search_fields = ('phone_number', 'email')