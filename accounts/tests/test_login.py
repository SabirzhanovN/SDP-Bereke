from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User

class LoginViewTest(TestCase):
    def setUp(self):
        self.username = 'testuser'
        self.password = 'testpass123'
        self.user = User.objects.create_user(username=self.username, password=self.password)

    def test_login_success(self):
        response = self.client.post(reverse('login'), {
            'username': self.username,
            'password': self.password,
        })
        self.assertRedirects(response, reverse('home'))
        user = response.wsgi_request.user
        self.assertTrue(user.is_authenticated)

    def test_login_fail(self):
        response = self.client.post(reverse('login'), {
            'username': self.username,
            'password': 'wrongpassword',
        })

        self.assertEqual(response.status_code, 200)
        user = response.wsgi_request.user
        self.assertFalse(user.is_authenticated)
        messages = list(response.context['messages'])
        self.assertTrue(any('Неверное имя пользователя' in str(m) for m in messages))
