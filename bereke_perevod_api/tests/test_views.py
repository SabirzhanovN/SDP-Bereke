import datetime

from django.http import Http404
from django.test import TestCase
from django.utils.timezone import make_aware
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate
from django.urls import reverse
from django.contrib.auth.models import User

from bereke_perevod_api.models import UploadedP12
from bereke_perevod_api.views import FileDownloadView


class CertCreateViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('file-create')  # замени на реальный URL

        # Создаём пользователя и логинимся
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')

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

    def test_create_cert_success(self):
        response = self.client.post(self.url, data=self.valid_data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['message'], 'Сертификат создан')

    def test_create_cert_password_mismatch(self):
        data = self.valid_data.copy()
        data['password2'] = 'wrongpass'
        response = self.client.post(self.url, data=data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('non_field_errors', response.data)
        self.assertTrue(any('Пароли не совпадают' in msg for msg in response.data.get('non_field_errors', [])))

    def test_create_cert_invalid_expiration(self):
        data = self.valid_data.copy()
        data['expiration'] = 0
        response = self.client.post(self.url, data=data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('non_field_errors', response.data)
        self.assertTrue(any('Срок действия' in msg for msg in response.data.get('non_field_errors', [])))

    def test_unauthenticated_access_denied(self):
        self.client.logout()
        response = self.client.post(self.url, data=self.valid_data, format='json')
        self.assertIn(response.status_code, [401, 403])


class CertDeleteViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')

        self.cert = UploadedP12.objects.create(
            filename='testcert.p12',
            file_data=b'test binary data'
        )

    def test_delete_cert_success(self):
        url = reverse('file-delete', kwargs={'pk': self.cert.pk})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.data['message'], 'Сертификат удален!')
        self.assertFalse(UploadedP12.objects.filter(pk=self.cert.pk).exists())

    def test_delete_cert_not_found(self):
        url = reverse('file-delete', kwargs={'pk': 9999})  # несуществующий pk
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data['error'], 'Сертификат не найден!')

    def test_unauthenticated_delete_denied(self):
        self.client.logout()
        url = reverse('file-delete', kwargs={'pk': self.cert.pk})
        response = self.client.delete(url)
        self.assertIn(response.status_code, [401, 403])



class CertListViewTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.client.login(username='testuser', password='testpass123')

        # Создаём тестовые сертификаты с разными именами и датами
        self.cert1 = UploadedP12.objects.create(
            filename="25AB_asan.asanov.p12",
            uploaded_at=make_aware(datetime.datetime(2025, 7, 11, 14, 21, 34)),
            file_data=b'data1'
        )
        self.cert2 = UploadedP12.objects.create(
            filename="99ZZ_ivan.ivanov.p12",
            uploaded_at=make_aware(datetime.datetime(2025, 7, 10, 9, 0, 0)),
            file_data=b'data2'
        )
        self.url = reverse('files')

    def test_get_list_no_filters(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('results', response.data)
        self.assertGreaterEqual(len(response.data['results']), 2)

    def test_search_by_filename(self):
        # Поиск с точным совпадением
        response = self.client.get(self.url, {'search': 'asanov'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any('asanov' in item['filename'] for item in response.data['results']))



    def test_filter_by_date(self):
        response = self.client.get(self.url, {'date': '2025-07-11'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(item['uploaded_at'].startswith('2025-07-11') for item in response.data['results']))

    def test_pagination(self):
        response = self.client.get(self.url, {'page': 1})
        self.assertEqual(response.status_code, 200)
        self.assertIn('count', response.data)
        self.assertIn('next', response.data)
        self.assertIn('previous', response.data)
        self.assertIn('results', response.data)

    def test_unauthenticated_access_denied(self):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertIn(response.status_code, [401, 403])


class FileDownloadViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')

        self.file_data = b'test binary data'
        self.cert = UploadedP12.objects.create(
            filename='testcert.p12',
            file_data=self.file_data
        )
        self.factory = APIRequestFactory()

    def test_download_file_success(self):
        url = reverse('file-download', args=[self.cert.pk])
        request = self.factory.get(url)
        force_authenticate(request, user=self.user)

        response = FileDownloadView.as_view()(request, pk=self.cert.pk)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Disposition'], f'attachment; filename="{self.cert.filename}"')
        self.assertIn(response['Content-Type'], ['application/octet-stream', 'application/x-pkcs12'])

        content = b''.join(response.streaming_content)
        self.assertEqual(content, self.file_data)

    def test_download_file_not_found(self):
        url = reverse('file-download', args=[99999])
        request = self.factory.get(url)
        force_authenticate(request, user=self.user)

        response = FileDownloadView.as_view()(request, pk=99999)
        self.assertEqual(response.status_code, 404)
