from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from .models import CustomUser

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        try:
            data = super().validate(attrs)
            # Add ONLY existing fields from CustomUser model
            data['email'] = self.user.email
            data['role'] = self.user.role
            data['can_create_orders'] = self.user.can_create_orders
            data['can_generate_bills'] = self.user.can_generate_bills  
            data['can_access_kitchen'] = self.user.can_access_kitchen
            data['is_active'] = self.user.is_active
            return data
        except AuthenticationFailed:
            raise AuthenticationFailed(detail="Invalid email or password.")
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['email'] = user.email
        token['role'] = user.role
        token['can_create_orders'] = user.can_create_orders
        token['can_generate_bills'] = user.can_generate_bills
        token['can_access_kitchen'] = user.can_access_kitchen
        return token

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'role', 'can_create_orders', 'can_generate_bills', 'can_access_kitchen', 'is_active']

class UserRoleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['role', 'can_create_orders', 'can_generate_bills', 'can_access_kitchen']
