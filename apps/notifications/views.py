from rest_framework import generics, permissions
from .models import NotificationRecipient
from .serializers import NotificationRecipientSerializer
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse

class NotificationRecipientListCreateView(generics.ListCreateAPIView):
    queryset = NotificationRecipient.objects.all()
    serializer_class = NotificationRecipientSerializer
    permission_classes = [permissions.IsAuthenticated]

class NotificationRecipientRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = NotificationRecipient.objects.all()
    serializer_class = NotificationRecipientSerializer
    permission_classes = [permissions.IsAuthenticated]

@csrf_exempt
def twilio_delivery_status(request):
    if request.method == "POST":
        status = request.POST.get("MessageStatus")
        sid = request.POST.get("MessageSid")
        to = request.POST.get("To")
        # You can log this info or update your Notification model
        print(f"Twilio delivery for {to}: {status} (SID: {sid})")
        return HttpResponse("OK")
    return HttpResponse("Method not allowed", status=405)
