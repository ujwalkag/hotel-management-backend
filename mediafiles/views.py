from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser
from apps.utils.oracle_storage import upload_file_to_oracle   # adjust import path

class UploadMediaView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request):
        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return Response({"error": "No file uploaded."}, status=400)

        file_url = upload_file_to_oracle(uploaded_file, uploaded_file.name)
        if file_url:
            return Response({"url": file_url})
        return Response({"error": "Upload failed"}, status=500)

