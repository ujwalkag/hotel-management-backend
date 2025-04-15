from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = 'email'

    def validate(self, attrs):
        attrs['username'] = attrs.get('email')  # Internally map to username
        data = super().validate(attrs)

        data['email'] = self.user.email  # Or data['name'] = self.user.get_full_name() if you prefer
        data['role'] = self.user.role
        return data

