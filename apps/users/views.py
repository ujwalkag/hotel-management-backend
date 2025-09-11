from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, AllowAny, IsAuthenticated
from rest_framework.decorators import action
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction
from .models import CustomUser
from .serializers import CustomTokenObtainPairSerializer, UserSerializer

from rest_framework.decorators import api_view, permission_classes
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import logging

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def options(self, request, *args, **kwargs):
        """Handle preflight OPTIONS request"""
        response = Response()
        response["Access-Control-Allow-Origin"] = request.META.get('HTTP_ORIGIN', '*')
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
        response["Access-Control-Allow-Credentials"] = "true"
        return response

    def post(self, request, *args, **kwargs):
        """Enhanced POST with proper CORS headers"""
        logger.info(f"Authentication request from: {request.META.get('HTTP_ORIGIN', 'Unknown')}")

        try:
            response = super().post(request, *args, **kwargs)

            # Add CORS headers to response
            origin = request.META.get('HTTP_ORIGIN')
            if origin in ['https://hotelrshammad.co.in', 'https://www.hotelrshammad.co.in']:
                response["Access-Control-Allow-Origin"] = origin
                response["Access-Control-Allow-Credentials"] = "true"

            logger.info("Authentication successful")
            return response

        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            response = Response(
                {'error': 'Authentication failed', 'detail': str(e)}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

            # Add CORS headers even to error responses
            origin = request.META.get('HTTP_ORIGIN')
            if origin in ['https://hotelrshammad.co.in', 'https://www.hotelrshammad.co.in']:
                response["Access-Control-Allow-Origin"] = origin
                response["Access-Control-Allow-Credentials"] = "true"

            return response
class IsAdminRole(BasePermission):
    """Permission class to check if user has admin role"""
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, "role", None) == "admin"

class StaffUserViewSet(viewsets.ViewSet):
    """ViewSet for managing staff users"""
    permission_classes = [IsAuthenticated]  # NOW PROPERLY IMPORTED
    
    def create(self, request):
        """Create a new staff user with role and permissions"""
        try:
            email = request.data.get("email", "").strip().lower()
            password = request.data.get("password", "").strip()
            role = request.data.get("role", "staff")
            
            # Validation
            if not email or not password:
                return Response(
                    {"error": "Email and password are required."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if len(password) < 6:
                return Response(
                    {"error": "Password must be at least 6 characters long."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if CustomUser.objects.filter(email=email).exists():
                return Response(
                    {"error": "Email already exists."}, 
                    status=status.HTTP_409_CONFLICT
                )
            
            # Validate role
            valid_roles = ['admin', 'staff', 'waiter', 'biller']
            if role not in valid_roles:
                return Response(
                    {"error": f"Invalid role. Must be one of: {', '.join(valid_roles)}"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create user with role and auto-assign permissions
            with transaction.atomic():
                user = CustomUser.objects.create_user(
                    email=email,
                    password=password,
                    role=role
                )
                
                # Auto-assign permissions based on role
                if role == 'admin':
                    user.can_create_orders = True
                    user.can_generate_bills = True
                    user.can_access_kitchen = True
                elif role == 'waiter':
                    user.can_create_orders = True
                    user.can_generate_bills = False
                    user.can_access_kitchen = False
                elif role == 'staff':
                    user.can_create_orders = True
                    user.can_generate_bills = True
                    user.can_access_kitchen = True
                elif role == 'biller':
                    user.can_create_orders = False
                    user.can_generate_bills = True
                    user.can_access_kitchen = False
                
                user.save()
                
                return Response({
                    'message': f'{role.capitalize()} user created successfully',
                    'user': UserSerializer(user).data
                }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            return Response(
                {'error': f'Failed to create user: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def list(self, request):
        """List all staff users"""
        try:
            staff_users = CustomUser.objects.filter(role__in=['staff', 'waiter', 'biller', 'admin'])
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

    def retrieve(self, request, pk=None):
        """Retrieve a specific staff user"""
        try:
            user = CustomUser.objects.get(id=pk)
            serializer = UserSerializer(user)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "User not found."}, 
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
            user = CustomUser.objects.get(id=pk)
            
            # Prevent role change through this endpoint
            if 'role' in request.data:
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
                {"error": "User not found."}, 
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
            user = CustomUser.objects.get(id=pk)
            
            # Prevent deleting admin if not admin
            if user.role == 'admin' and request.user.role != 'admin':
                return Response(
                    {"error": "Cannot delete admin users."}, 
                    status=status.HTTP_403_FORBIDDEN
                )
            
            user_email = user.email
            user.delete()
            
            return Response({
                'message': f'User {user_email} deleted successfully'
            }, status=status.HTTP_200_OK)
            
        except CustomUser.DoesNotExist:
            return Response(
                {"error": "User not found."}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Failed to delete user: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['patch'])
    def update_permissions(self, request, pk=None):
        """Update user role and permissions"""
        try:
            user = CustomUser.objects.get(id=pk)
            
            # Get new role and permissions
            new_role = request.data.get('role', user.role)
            can_create_orders = request.data.get('can_create_orders', user.can_create_orders)
            can_generate_bills = request.data.get('can_generate_bills', user.can_generate_bills)
            can_access_kitchen = request.data.get('can_access_kitchen', user.can_access_kitchen)
            
            # Validate role
            valid_roles = ['admin', 'staff', 'waiter', 'biller']
            if new_role not in valid_roles:
                return Response(
                    {'error': f'Invalid role. Must be one of: {", ".join(valid_roles)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update user
            user.role = new_role
            user.can_create_orders = can_create_orders
            user.can_generate_bills = can_generate_bills
            user.can_access_kitchen = can_access_kitchen
            user.save()
            
            return Response({
                'message': 'Permissions updated successfully',
                'user': UserSerializer(user).data
            }, status=status.HTTP_200_OK)
            
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
