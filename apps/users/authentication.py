# apps/users/authentication.py - COMPLETE FIX
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from django.contrib.auth import get_user_model
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class CustomJWTAuthentication(JWTAuthentication):
    """
    Enhanced JWT Authentication with proper error handling and logging
    """

    def get_user(self, validated_token):
        """
        Return the user associated with the given validated token.
        Enhanced with better error handling and logging.
        """
        try:
            # Get user from parent class
            user = super().get_user(validated_token)

            if not user:
                logger.error("User not found for validated token")
                raise InvalidToken("User not found")

            if not user.is_active:
                logger.error(f"Inactive user attempted authentication: {user.email}")
                raise InvalidToken("User account is disabled")

            # Attach custom claims from token to user object
            user.role = validated_token.get("role", getattr(user, "role", None))
            user.email = validated_token.get("email", getattr(user, "email", None))
            user.can_create_orders = validated_token.get("can_create_orders", getattr(user, "can_create_orders", False))
            user.can_generate_bills = validated_token.get("can_generate_bills", getattr(user, "can_generate_bills", False))
            user.can_access_kitchen = validated_token.get("can_access_kitchen", getattr(user, "can_access_kitchen", False))

            logger.info(f"Successful authentication for user: {user.email} (role: {user.role})")
            return user

        except User.DoesNotExist:
            logger.error("User does not exist for validated token")
            raise InvalidToken("User not found")
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise InvalidToken(f"Authentication failed: {str(e)}")

    def authenticate(self, request):
        """
        Enhanced authenticate method with better logging
        """
        try:
            result = super().authenticate(request)
            if result:
                user, token = result
                logger.debug(f"Authentication successful for {user.email}")
            return result
        except Exception as e:
            logger.error(f"Authentication exception: {str(e)}")
            raise
