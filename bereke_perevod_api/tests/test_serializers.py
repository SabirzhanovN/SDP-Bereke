from django.test import TestCase
from rest_framework.reverse import reverse


from bereke_perevod_api.serializers import CertCreateSerializer, UploadedP12Serializer
from bereke_perevod_api.models import UploadedP12

from rest_framework.test import APIRequestFactory

class CertCreateSerializerTest(TestCase):
    def setUp(self):
        self.valid_data = {
            'filename': 'testcert',
            'expiration': 365,
            'password': 'strongpass123',
            'password2': 'strongpass123',
            'full_name': 'Иван Иванов',
            'department': 'IT',
            'organization': 'Айыл Банк',
            'city': 'г.Бишкек',
            'region': 'Чуй',
            'country_code': 'KG',
        }

    def test_passwords_must_match(self):
        """Проверка: если пароли не совпадают, сериализатор должен выдать ошибку валидации"""
        data = self.valid_data.copy()
        data['password2'] = 'wrongpass'
        serializer = CertCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('Пароли не совпадают.', str(serializer.errors))

    def test_expiration_range(self):
        """Проверка: expiration должен быть в диапазоне 1-365"""
        data = self.valid_data.copy()

        # Проверим expiration = 0 (невалидно)
        data['expiration'] = 0
        serializer = CertCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('Срок действия', str(serializer.errors))

        # Проверим expiration = 366 (невалидно)
        data['expiration'] = 366
        serializer = CertCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('Срок действия', str(serializer.errors))

        # Проверим expiration = 1 (валидно)
        data['expiration'] = 1
        serializer = CertCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_create_uploaded_p12_instance(self):
        """Проверка успешного создания UploadedP12 с корректными данными"""
        serializer = CertCreateSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid(), serializer.errors)
        obj = serializer.save()
        self.assertIsNotNone(obj)
        self.assertEqual(obj.filename, self.valid_data['filename'] + '.p12')
        self.assertTrue(obj.file_data)  # Данные сертификата должны присутствовать в файле
        self.assertTrue(UploadedP12.objects.filter(id=obj.id).exists())


class UploadedP12SerializerTest(TestCase):
    def setUp(self):
        self.obj = UploadedP12.objects.create(
            filename='testcert.p12',
            file_data=b'test binary data'
        )
        self.factory = APIRequestFactory()
        self.request = self.factory.get('/')  # фиктивный запрос для контекста

    def test_serialization_fields(self):
        """Проверяем что сериализатор корректно сериализует основные поля"""
        serializer = UploadedP12Serializer(instance=self.obj, context={'request': self.request})
        data = serializer.data

        self.assertEqual(data['id'], self.obj.id)
        self.assertEqual(data['filename'], self.obj.filename)
        self.assertIsNotNone(data['uploaded_at'])
        self.assertIn('file', data)

    def test_file_field_url(self):
        """Проверяем, что поле 'file' содержит правильный URL"""
        serializer = UploadedP12Serializer(instance=self.obj, context={'request': self.request})
        data = serializer.data
        expected_url = reverse('file-download', kwargs={'pk': self.obj.pk}, request=self.request)
        self.assertEqual(data['file'], expected_url)

    def test_file_field_without_request_context(self):
        """Если контекст request отсутствует, поле 'file' должно быть None"""
        serializer = UploadedP12Serializer(instance=self.obj)
        data = serializer.data
        self.assertIsNone(data['file'])