from rest_framework import serializers
from .models import StaffProfile, Attendance, Payroll

class StaffProfileSerializer(serializers.ModelSerializer):
    department_display = serializers.CharField(source='get_department_display', read_only=True)
    employment_type_display = serializers.CharField(source='get_employment_type_display', read_only=True)
    age = serializers.SerializerMethodField()
    
    class Meta:
        model = StaffProfile
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def get_age(self, obj):
        if obj.hire_date:
            from datetime import date
            today = date.today()
            return today.year - obj.hire_date.year - ((today.month, today.day) < (obj.hire_date.month, obj.hire_date.day))
        return None

    def validate_email(self, value):
        if StaffProfile.objects.filter(email=value).exists():
            if self.instance and self.instance.email != value:
                raise serializers.ValidationError("Email already exists.")
        return value

class AttendanceSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.name', read_only=True)
    staff_id = serializers.CharField(source='staff.employee_id', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Attendance
        fields = '__all__'
        read_only_fields = ['total_hours', 'overtime_hours', 'created_at', 'updated_at']

    def create(self, validated_data):
        attendance = super().create(validated_data)
        attendance.calculate_hours()
        return attendance

    def update(self, instance, validated_data):
        attendance = super().update(instance, validated_data)
        attendance.calculate_hours()
        return attendance

class PayrollSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.name', read_only=True)
    staff_id = serializers.CharField(source='staff.employee_id', read_only=True)
    payment_method_display = serializers.CharField(source='get_payment_method_display', read_only=True)
    gross_amount = serializers.SerializerMethodField()
    
    class Meta:
        model = Payroll
        fields = '__all__'
        read_only_fields = [
            'days_worked', 'total_hours', 'overtime_hours', 
            'basic_amount', 'overtime_amount', 'net_amount',
            'created_at', 'updated_at'
        ]

    def get_gross_amount(self, obj):
        return obj.basic_amount + obj.overtime_amount + obj.bonus + obj.allowances

    def create(self, validated_data):
        payroll = super().create(validated_data)
        payroll.calculate_payroll()
        return payroll
```

### 4. Staff URLs - apps/staff/urls.py (FIXED)

```python
# apps/staff/urls.py - FIXED VERSION
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'profiles', views.StaffProfileViewSet, basename='staff-profile')  # FIXED - Now exists!
router.register(r'attendance', views.AttendanceViewSet, basename='attendance')
router.register(r'payroll', views.PayrollViewSet, basename='payroll')

urlpatterns = [
    path('', include(router.urls)),
]
```

### 5. Staff Admin - apps/staff/admin.py (COMPLETE)

```python
# apps/staff/admin.py - COMPLETE ADMIN
from django.contrib import admin
from .models import StaffProfile, Attendance, Payroll

@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'name', 'department', 'position', 'employment_type', 'is_active']
    list_filter = ['department', 'employment_type', 'is_active']
    search_fields = ['employee_id', 'name', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'employee_id', 'department', 'position', 'employment_type')
        }),
        ('Contact Information', {
            'fields': ('email', 'phone', 'address', 'emergency_contact', 'emergency_phone')
        }),
        ('Employment Details', {
            'fields': ('basic_salary', 'hourly_rate', 'hire_date', 'is_active')
        }),
    )

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ['staff', 'date', 'check_in', 'check_out', 'status', 'total_hours']
    list_filter = ['status', 'date', 'staff__department']
    search_fields = ['staff__name', 'staff__employee_id']
    date_hierarchy = 'date'
    readonly_fields = ['total_hours', 'overtime_hours']

@admin.register(Payroll)
class PayrollAdmin(admin.ModelAdmin):
    list_display = ['staff', 'month', 'year', 'net_amount', 'is_paid']
    list_filter = ['month', 'year', 'is_paid', 'staff__department']
    search_fields = ['staff__name', 'staff__employee_id']
    readonly_fields = ['days_worked', 'total_hours', 'net_amount']
