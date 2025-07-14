from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.messages import get_messages

class LogoutViewTest(TestCase):
    def setUp(self):
        self.username = 'testuser'
        self.password = 'testpass123'
        self.user = User.objects.create_user(username=self.username, password=self.password)

    def test_logout(self):
        self.client.login(username=self.username, password=self.password)

        response = self.client.get(reverse('logout'), follow=True)

        self.assertRedirects(response, reverse('login'))

        user = response.context['user']
        self.assertFalse(user.is_authenticated)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Вы успешно вышли из системы.' in str(m) for m in messages))
