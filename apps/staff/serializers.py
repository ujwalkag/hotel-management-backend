from rest_framework import serializers
from .models import StaffProfile, AttendanceRecord, AdvancePayment

class StaffProfileSerializer(serializers.ModelSerializer):
    department_display = serializers.CharField(source='get_department_display', read_only=True)
    employment_type_display = serializers.CharField(source='get_employment_type_display', read_only=True)
    
    class Meta:
        model = StaffProfile
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class AttendanceRecordSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = AttendanceRecord
        fields = '__all__'
        read_only_fields = ['created_at']

class AdvancePaymentSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source='staff.name', read_only=True)
    
    class Meta:
        model = AdvancePayment
        fields = '__all__'
        read_only_fields = ['created_at']
