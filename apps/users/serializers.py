from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from .models import CustomUser

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        try:
            data = super().validate(attrs)
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
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = [
            'id',
            'email',
            'password',
            'role',
            'can_create_orders',
            'can_generate_bills',
            'can_access_kitchen',
            'is_active',
        ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = CustomUser(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

class UserRoleUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['role', 'can_create_orders', 'can_generate_bills', 'can_access_kitchen']

