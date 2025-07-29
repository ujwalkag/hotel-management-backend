# apps/users/authentication.py

#from rest_framework_simplejwt.authentication import JWTAuthentication

#class CustomJWTAuthentication(JWTAuthentication):
#    def get_user(self, validated_token):
#        user = super().get_user(validated_token)
#        user.role = validated_token.get("role", None)
#        user.email = validated_token.get("email", None)
#        return user
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT Authentication that attaches `role` and `email` to the user object from the token.
    """

    def get_user(self, validated_token):
        """
        Return the user associated with the given validated token.
        Also attaches the `role` and `email` claims to the user object.
        """
        try:
            user = super().get_user(validated_token)
        except Exception as e:
            raise InvalidToken(f"User not found: {str(e)}")

        # Attach custom claims to the user object if present in the token
        user.role = validated_token.get("role", getattr(user, "role", None))
        user.email = validated_token.get("email", getattr(user, "email", None))
        return user
