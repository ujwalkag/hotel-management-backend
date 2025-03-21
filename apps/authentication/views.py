from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            # Dummy authentication logic
            if username == 'admin' and password == 'password':
                return JsonResponse({'message': 'Login successful', 'token': 'dummy-jwt-token'}, status=200)
            else:
                return JsonResponse({'error': 'Invalid credentials'}, status=401)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)

