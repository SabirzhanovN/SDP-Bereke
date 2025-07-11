from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.backends import default_backend
import datetime

from rest_framework import serializers
from rest_framework.reverse import reverse

from .models import UploadedP12


class CertCreateSerializer(serializers.Serializer):
    """
    Serializer for creating and saving a PKCS#12 (.p12) certificate.

    Validates user input, ensures passwords match and expiration is within valid range (1–365 days),
    then generates a structured certificate as text or binary format and stores it in the database.

    Fields:
        - filename: Name of the certificate file (without extension)
        - expiration: Validity period of the certificate in days (1–365)
        - password: Password to encrypt the certificate (write-only)
        - password2: Confirmation of the password (write-only)
        - full_name: Full name of the certificate owner
        - department: Department or organizational unit
        - organization: Organization name
        - city: City or locality
        - region: Region or state
        - country_code: Country code in ISO 3166-1 alpha-2 format

    Validations:
        - Passwords must match
        - Expiration must be between 1 and 365 days

    On success, creates a .p12 file (currently as encoded text) and saves it to the UploadedP12 model.
    """
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
        # Генерация ключа
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # Данные владельца
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, validated_data['country_code']),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, validated_data['region']),
            x509.NameAttribute(NameOID.LOCALITY_NAME, validated_data['city']),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, validated_data['organization']),
            x509.NameAttribute(NameOID.ORGANIZATIONAL_UNIT_NAME, validated_data['department']),
            x509.NameAttribute(NameOID.COMMON_NAME, validated_data['full_name']),
        ])

        expiration_days = validated_data['expiration']
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=expiration_days))
            .sign(private_key=key, algorithm=hashes.SHA256(), backend=default_backend())
        )

        # Сборка PKCS#12 (.p12)
        p12_data = pkcs12.serialize_key_and_certificates(
            name=validated_data['full_name'].encode(),
            key=key,
            cert=cert,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(validated_data['password'].encode())
        )

        # Сохраняем в БД
        return UploadedP12.objects.create(
            filename=validated_data['filename'] + '.p12',
            file_data=p12_data
        )


class UploadedP12Serializer(serializers.ModelSerializer):
    """
    Serializer for representing uploaded .p12 certificates.

    Adds a dynamic 'file' field that provides a download URL for the certificate.
    This URL is constructed using the request context and the certificate's primary key.

    Fields:
        - id: Unique identifier of the certificate
        - filename: Name of the uploaded certificate file (e.g., "user01.p12")
        - uploaded_at: Timestamp when the certificate was uploaded
        - file: URL to download the certificate (constructed dynamically)
    """
    file = serializers.SerializerMethodField()

    class Meta:
        model = UploadedP12
        fields = ['id', 'filename', 'uploaded_at', 'file']

    def get_file(self, obj):
        request = self.context.get('request')
        if request:
            return reverse('file-download', kwargs={'pk': obj.pk}, request=request)
        return None
