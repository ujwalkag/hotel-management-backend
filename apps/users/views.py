from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, AllowAny
from rest_framework.decorators import action  # FIXED: Added missing import
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from .models import CustomUser
from .serializers import CustomTokenObtainPairSerializer, UserSerializer


class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token obtain pair view for JWT authentication"""
    serializer_class = CustomTokenObtainPairSerializer


class IsAdminRole(BasePermission):
    """Permission class to check if user has admin role"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, "role", None) == "admin"


# FIXED: Added UserRoleUpdateSerializer class since it was referenced but missing
class UserRoleUpdateSerializer:
    """Serializer for updating user roles - placeholder implementation"""
    def __init__(self, instance, data=None, partial=False):
        self.instance = instance
        self.data = data
        self.partial = partial
    
    def is_valid(self):
        # Basic validation - you can extend this based on your requirements
        if self.data and 'role' in self.data:
            valid_roles = ['admin', 'staff', 'guest']
            return self.data['role'] in valid_roles
        return False
    
    def save(self):
        if self.data and 'role' in self.data:
            self.instance.role = self.data['role']
            self.instance.save()
    
    @property
    def errors(self):
        return {"role": "Invalid role specified"}


class StaffUserViewSet(viewsets.ViewSet):
    """ViewSet for managing staff users"""
    permission_classes = [IsAdminRole]
    
    @action(detail=True, methods=['patch'])  # FIXED: Now action is properly imported
    def update_permissions(self, request, pk=None):
        """Update user role and permissions"""
        try:
            user = CustomUser.objects.get(id=pk)
            if user.role == 'admin':
                return Response(
                    {'error': 'Cannot modify admin permissions'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = UserRoleUpdateSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'message': 'Permissions updated successfully',
                    'user': UserSerializer(user).data
                }, status=status.HTTP_200_OK)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except CustomUser.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'An error occurred: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def list(self, request):
        """List all staff users"""
        try:
            staff_users = CustomUser.objects.filter(role="staff")
            serializer = UserSerializer(staff_users, many=True)
            return Response({
                'count': staff_users.count(),
                'results': serializer.data
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve staff users: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def create(self, request):
        """Create a new staff user"""
        try:
            email = request.data.get("email", "").strip().lower()
            password = request.data.get("password", "").strip()
            first_name = request.data.get("first_name", "").strip()
            last_name = request.data.get("last_name", "").strip()
            
            # Validation
            if not email or not password:
                return Response(
                    {"error": "Email and password are required."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if len(password) < 8:
                return Response(
                    {"error": "Password must be at least 8 characters long."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if CustomUser.objects.filter(email=email).exists():
                return Response(
                    {"error": "Email already exists."}, 
                    status=status.HTTP_409_CONFLICT
                )
            
            # Create user
            with transaction.atomic():
                user_data = {
                    'email': email,
                    'password': password,
                    'role': "staff"
                }
                if first_name:
                    user_data['first_name'] = first_name
                if last_name:
                    user_data['last_name'] = last_name
                
                user = CustomUser.objects.create_user(**user_data)
            
            return Response({
                'message': 'Staff user created successfully',
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to create user: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def retrieve(self, request, pk=None):
        """Retrieve a specific staff user"""
        try:
            user = CustomUser.objects.get(id=pk, role="staff")
            serializer = UserSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Staff user not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve user: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, pk=None):
        """Update a staff user"""
        try:
            user = CustomUser.objects.get(id=pk, role="staff")
            
            # Prevent role change through this endpoint
            if 'role' in request.data and request.data['role'] != 'staff':
                return Response(
                    {'error': 'Use update_permissions endpoint to change user roles'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            serializer = UserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'message': 'User updated successfully',
                    'user': serializer.data
                }, status=status.HTTP_200_OK)
            
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Staff user not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to update user: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, pk=None):
        """Delete a staff user"""
        try:
            user = CustomUser.objects.get(id=pk, role="staff")
            user_email = user.email  # Store for response
            user.delete()
            return Response({
                'message': f'Staff user {user_email} deleted successfully'
            }, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "Staff user not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to delete user: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class LogoutView(APIView):
    """Handle user logout by blacklisting refresh token"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Logout user by blacklisting refresh token"""
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response(
                    {"error": "Refresh token required."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response(
                {"message": "Logout successful"}, 
                status=status.HTTP_200_OK
            )
            
        except Exception as e:
            return Response(
                {"error": "Invalid token or already logged out"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
