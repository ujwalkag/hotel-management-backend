from django.http import JsonResponse

def book_room(request):
    return JsonResponse({"message": "Room booked successfully!"})

def cancel_booking(request):
    return JsonResponse({"message": "Booking canceled successfully!"})

