from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from utils.oracle_storage import upload_file_to_oracle

class UploadMediaView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({"error": "No file provided"}, status=400)

        object_name = f"user_uploads/{request.user.id}/{file.name}"
        file_url = upload_file_to_oracle(file, object_name)
        return Response({"url": file_url}, status=201)

