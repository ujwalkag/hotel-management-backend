from rest_framework_simplejwt.authentication import JWTAuthentication

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        user.role = validated_token.get("role", None)
        user.email = validated_token.get("email", None)
        return user

