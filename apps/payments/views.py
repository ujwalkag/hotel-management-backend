from django.http import JsonResponse

def stripe_payment(request):
    return JsonResponse({"message": "Stripe payment initiated successfully!"})

def razorpay_payment(request):
    return JsonResponse({"message": "Razorpay payment initiated successfully!"})

