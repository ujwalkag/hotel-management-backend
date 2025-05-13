from rest_framework import serializers
from .models import NotificationRecipient

class NotificationRecipientSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationRecipient
        fields = '__all__'

