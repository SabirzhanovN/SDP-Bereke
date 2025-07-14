import io
import re

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.http import Http404, FileResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .auth import CsrfExemptSessionAuthentication
from .models import UploadedP12
from .serializers import CertCreateSerializer, UploadedP12Serializer


class CertCreateView(APIView):
    """
    Accepts form data, generates a pseudo .p12 certificate as plain text,
    and saves it in the database as binary content.
    Returns a success message if creation is successful, otherwise returns validation errors.
    """
    authentication_classes = [CsrfExemptSessionAuthentication]
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=[
                'filename', 'expiration', 'password', 'password2',
                'full_name', 'department', 'organization',
                'city', 'region', 'country_code'
            ],
            properties={
                'filename': openapi.Schema(type=openapi.TYPE_STRING, example='my_certificate'),
                'expiration': openapi.Schema(type=openapi.TYPE_INTEGER, example=365),
                'password': openapi.Schema(type=openapi.TYPE_STRING, format='password', example='secret123'),
                'password2': openapi.Schema(type=openapi.TYPE_STRING, format='password', example='secret123'),
                'full_name': openapi.Schema(type=openapi.TYPE_STRING, example='John Doe'),
                'department': openapi.Schema(type=openapi.TYPE_STRING, example='IT Department'),
                'organization': openapi.Schema(type=openapi.TYPE_STRING, example='MyCompany'),
                'city': openapi.Schema(type=openapi.TYPE_STRING, example='Bishkek'),
                'region': openapi.Schema(type=openapi.TYPE_STRING, example='Chuy'),
                'country_code': openapi.Schema(type=openapi.TYPE_STRING, example='KG'),
            }
        ),
        responses={
            201: openapi.Response(
                description="Успешное создание",
                examples={"application/json": {"message": "Сертификат создан"}}
            ),
            400: openapi.Response(
                description="Ошибки валидации",
                examples={
                    "application/json": {
                        "password2": ["Пароли не совпадают."],
                        "expiration": ["Срок действия (expiration) должен быть от 1 до 365 дней."]
                    }
                }
            )
        },
        operation_summary="Создание сертификата",
        operation_description="Создаёт .p12 сертификат и сохраняет в базу данных в виде бинарного контента."
    )

    def post(self, request):
        serializer = CertCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Сертификат создан'}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CertDeleteView(APIView):
    """
    Deletes a specific uploaded .p12 certificate by ID.
    """

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                name='pk',
                in_=openapi.IN_PATH,
                description='ID сертификата для удаления',
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            204: openapi.Response(
                description="Сертификат успешно удалён",
                examples={
                    "application/json": {"message": "Сертификат удален!"}
                }
            ),
            404: openapi.Response(
                description="Сертификат не найден",
                examples={
                    "application/json": {"error": "Сертификат не найден!"}
                }
            ),
        },
        operation_summary="Удаление сертификата",
        operation_description="Удаляет загруженный сертификат (.p12) по его идентификатору."
    )
    def delete(self, request, pk):
        try:
            file_obj = UploadedP12.objects.get(pk=pk)
        except UploadedP12.DoesNotExist:
            return Response({"error": "Сертификат не найден!"}, status=status.HTTP_404_NOT_FOUND)

        file_obj.delete()
        return Response({"message": "Сертификат удален!"}, status=status.HTTP_204_NO_CONTENT)


class CertListView(APIView):
    """
    Returns a list of uploaded .p12 certificates.
    Supports partial search by filename (?search=) and optional filter by upload date (?date=YYYY-MM-DD).
    Search is tolerant to symbols like -, _, . and spaces.
    """
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                name='search',
                in_=openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                required=False,
                description='Поиск по имени файла. Символы -, _, . и пробелы игнорируются.',
                example='asanov'
            ),
            openapi.Parameter(
                name='date',
                in_=openapi.IN_QUERY,
                type=openapi.FORMAT_DATE,
                required=False,
                description='Фильтрация по дате загрузки (формат YYYY-MM-DD)',
                example='2025-07-11'
            )
        ],
        responses={
            200: openapi.Response(
                description="Список сертификатов",
                examples={
                    "application/json": {
                        "count": 2,
                        "next": None,
                        "previous": None,
                        "results": [
                            {
                                "id": 1,
                                "filename": "25AB_asan.asanov.p12",
                                "uploaded_at": "2025-07-11T14:21:34Z"
                            },
                            {
                                "id": 2,
                                "filename": "99ZZ_ivan.ivanov.p12",
                                "uploaded_at": "2025-07-10T09:00:00Z"
                            }
                        ]
                    }
                }
            )
        },
        operation_summary="Список сертификатов",
        operation_description="Возвращает пагинированный список .p12 сертификатов с поддержкой поиска и фильтрации."
    )

    def get(self, request):
        search = request.query_params.get('search', '').strip()
        date_str = request.query_params.get('date', '').strip()

        queryset = UploadedP12.objects.all()

        if search:
            normalized_search = re.sub(r'[-_.]', ' ', search).lower()
            queryset = queryset.filter(
                Q(filename__icontains=search) |
                Q(filename__icontains=normalized_search)
            )

        if date_str:
            from django.utils.dateparse import parse_date
            parsed_date = parse_date(date_str)
            if parsed_date:
                queryset = queryset.filter(uploaded_at__date=parsed_date)

        paginator = PageNumberPagination()
        paginated_qs = paginator.paginate_queryset(queryset.order_by('-uploaded_at'), request)
        serializer = UploadedP12Serializer(paginated_qs, many=True, context={'request': request})

        return paginator.get_paginated_response(serializer.data)


class CertDetailView(APIView):
    """
    Retrieves detailed information about a specific uploaded certificate (.p12 file)
    by its primary key (ID). Returns metadata and optionally the file content.
    """
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                name='pk',
                in_=openapi.IN_PATH,
                description='ID сертификата',
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Информация о сертификате",
                examples={
                    "application/json": {
                        "id": 1,
                        "filename": "25AB_asan.asanov.p12",
                        "uploaded_at": "2025-07-11T14:21:34Z"
                    }
                }
            ),
            404: openapi.Response(
                description="Файл не найден",
                examples={
                    "application/json": {
                        "error": "File not found"
                    }
                }
            )
        },
        operation_summary="Детали сертификата",
        operation_description="Возвращает метаданные загруженного сертификата (.p12) по его идентификатору."
    )

    def get(self, request, pk):
        try:
            file_obj = UploadedP12.objects.get(pk=pk)
        except UploadedP12.DoesNotExist:
            return Response({"error": "File not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = UploadedP12Serializer(file_obj)
        return Response(serializer.data)


class FileDownloadView(APIView):
    """
    Download certificate via ID.
    """
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                name='pk',
                in_=openapi.IN_PATH,
                description='ID сертификата для скачивания',
                type=openapi.TYPE_INTEGER,
                required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Файл успешно скачан (ответ — application/octet-stream)",
                examples={
                    "application/json": {
                        "detail": "Файл будет загружен как вложение"
                    }
                }
            ),
            404: openapi.Response(
                description="Сертификат не найден",
                examples={
                    "application/json": {
                        "detail": "Not found."
                    }
                }
            ),
        },
        operation_summary="Скачивание сертификата",
        operation_description="Возвращает файл .p12 по заданному ID в виде вложения."
    )
    def get(self, request, pk):
        try:
            file_obj = UploadedP12.objects.get(pk=pk)
        except UploadedP12.DoesNotExist:
            raise Http404

        file_stream = io.BytesIO(file_obj.file_data)
        response = FileResponse(file_stream, as_attachment=True, filename=file_obj.filename)
        return response