from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from rest_framework import status
from rest_framework.generics import CreateAPIView
from authentication.serializers import UserSerializer
from authentication.permissions import IsAdminUser

User = get_user_model()

class CreateStaffUserView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def perform_create(self, serializer):
        serializer.save(password=make_password(self.request.data['password']))

class LoginView(APIView):
    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        user = User.objects.filter(email=email).first()

        if user and user.check_password(password):
            refresh = RefreshToken.for_user(user)
            return Response({
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "role": user.role
            })
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

class ResetPasswordView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, user_id):
        user = User.objects.filter(id=user_id, role='staff').first()
        if not user:
            return Response({"error": "Staff user not found"}, status=status.HTTP_404_NOT_FOUND)
        new_password = request.data.get("new_password")
        user.password = make_password(new_password)
        user.save()
        return Response({"message": "Password updated successfully"})
