# CRITICAL FIX 1: Complete CustomUser model with proper fields
# Replace your entire apps/users/models.py with this:

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
        ('kitchen_staff', 'Kitchen Staff'),
    )

    # Basic fields
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)  # ADDED THIS FIELD
    last_name = models.CharField(max_length=30, blank=True)   # ADDED THIS FIELD
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='staff')  # INCREASED LENGTH
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # Permission fields
    can_create_orders = models.BooleanField(default=False)
    can_generate_bills = models.BooleanField(default=False)
    can_access_kitchen = models.BooleanField(default=False)
    
    # Timestamps
    date_joined = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()
    
    def get_full_name(self):
        """
        Return the first_name plus last_name, separated by a space.
        Falls back to email if names are missing.
        """
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.email.split('@')[0] if self.email else "User"
    
    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name or self.email.split('@')[0] if self.email else "User"
    
    def save(self, *args, **kwargs):
        # Auto-assign permissions based on role
        if self.role == 'admin':
            self.can_create_orders = True
            self.can_generate_bills = True
            self.can_access_kitchen = True
            self.is_staff = True
        elif self.role == 'staff':
            self.can_create_orders = True
            self.can_generate_bills = True
            self.can_access_kitchen = False
        elif self.role == 'waiter':
            self.can_create_orders = True
            self.can_generate_bills = False
            self.can_access_kitchen = False
        elif self.role == 'kitchen_staff':
            self.can_create_orders = False
            self.can_generate_bills = False
            self.can_access_kitchen = True

        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.email
