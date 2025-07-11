import base64

from rest_framework import serializers
from rest_framework.reverse import reverse

from .models import UploadedP12

class CertCreateSerializer(serializers.Serializer):
    filename = serializers.CharField()
    expiration = serializers.IntegerField()
    password = serializers.CharField(write_only=True)
    password2 = serializers.CharField(write_only=True)
    full_name = serializers.CharField()
    department = serializers.CharField()
    organization = serializers.CharField()
    city = serializers.CharField()
    region = serializers.CharField()
    country_code = serializers.CharField()

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError("Пароли не совпадают.")

        if data['expiration'] <= 0 or data['expiration'] > 365:
            raise serializers.ValidationError("Срок действия (expiration) должен быть от 1 до 365 дней.")

        return data

    def create(self, validated_data):
        # Сборка содержимого в виде текста
        content = (
            f"Full Name: {validated_data['full_name']}\n"
            f"Department: {validated_data['department']}\n"
            f"Organization: {validated_data['organization']}\n"
            f"City: {validated_data['city']}\n"
            f"Region: {validated_data['region']}\n"
            f"Country Code: {validated_data['country_code']}\n"
            f"Expiration: {validated_data['expiration']}\n"
            f"Password: {validated_data['password']}\n"
        )

        # Преобразуем строку в бинарный поток
        binary_content = content.encode('utf-8')

        # Сохраняем в БД как .p12 (по сути — просто текст)
        return UploadedP12.objects.create(
            filename=validated_data['filename'] + '.p12',
            file_data=binary_content
        )


class UploadedP12Serializer(serializers.ModelSerializer):
    file = serializers.SerializerMethodField()

    class Meta:
        model = UploadedP12
        fields = ['id', 'filename', 'uploaded_at', 'file']

    def get_file(self, obj):
        request = self.context.get('request')
        if request:
            return reverse('file-download', kwargs={'pk': obj.pk}, request=request)
        return None

"""
{
"filename": "AB_test",
"expiration": 365,
"password": "1234",
"password2": "1234",
"full_name": "nurs sabir",
"department": "СБК 12-32",
"organization": "Айыл Банк",
"city": "г.Бишкек",
"region": "Чуй",
"country_code": "KG"
}
"""