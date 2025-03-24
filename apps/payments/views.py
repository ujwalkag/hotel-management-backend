from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


class PaymentStatusView(APIView):
    def get(self, request):
        return Response({"status": "Payment status endpoint working!"}, status=200)


# CSRF Exempt for Stripe Payment
@csrf_exempt
def stripe_payment(request):
    if request.method == "POST":
        # Add Stripe payment logic here
        return JsonResponse({"message": "Stripe payment initiated successfully!"})
    return JsonResponse({"error": "Invalid Request"}, status=400)


# CSRF Exempt for Razorpay Payment
@csrf_exempt
def razorpay_payment(request):
    if request.method == "POST":
        # Add Razorpay payment logic here
        return JsonResponse({"message": "Razorpay payment initiated successfully!"})
    return JsonResponse({"error": "Invalid Request"}, status=400)

