from django.http import JsonResponse

def notify_admin(request):
    # Simulate sending admin notification (we will refine this later)
    return JsonResponse({"message": "Admin notified successfully!"})

