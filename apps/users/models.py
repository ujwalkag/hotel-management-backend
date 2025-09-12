from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, role='staff', **extra_fields):
        if not email:
            raise ValueError("Email must be provided")
        email = self.normalize_email(email)
        user = self.model(email=email, role=role, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, role="admin", **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('staff', 'Staff'),
        ('waiter', 'Waiter'),
    )

    email = models.EmailField(unique=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)  # INCREASE to max_length=10
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # ADD THESE PERMISSION FIELDS
    can_create_orders = models.BooleanField(default=False)
    can_generate_bills = models.BooleanField(default=False)
    can_access_kitchen = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        # Auto-assign permissions based on role
        if self.role == 'admin':
            self.can_create_orders = True
            self.can_generate_bills = True
            self.can_access_kitchen = True
        elif self.role == 'waiter':
            self.can_generate_bills = False
            self.can_access_kitchen = False
        elif self.role == 'biller':
            self.can_create_orders = False
            self.can_access_kitchen = False

        super().save(*args, **kwargs)


    def __str__(self):
        return self.email

