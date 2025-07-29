from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from django.db import transaction

from .models import CustomUser
from .serializers import CustomTokenObtainPairSerializer, UserSerializer

from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, "role", None) == "admin"

class StaffUserViewSet(viewsets.ViewSet):
    permission_classes = [IsAdminRole]

    def list(self, request):
        staff_users = CustomUser.objects.filter(role="staff")
        serializer = UserSerializer(staff_users, many=True)
        return Response(serializer.data)

    def create(self, request):
        email = request.data.get("email", "").strip().lower()
        password = request.data.get("password", "").strip()
        if not email or not password:
            return Response({"error": "Email and password are required."}, status=status.HTTP_400_BAD_REQUEST)
        if CustomUser.objects.filter(email=email).exists():
            return Response({"error": "Email already exists."}, status=status.HTTP_409_CONFLICT)
        with transaction.atomic():
            user = CustomUser.objects.create_user(
                email=email, password=password, role="staff"
            )
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        try:
            user = CustomUser.objects.get(id=pk, role="staff")
            user.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except CustomUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)

class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "Refresh token required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception:
            return Response({"error": "Invalid token or already logged out"}, status=status.HTTP_400_BAD_REQUEST)
