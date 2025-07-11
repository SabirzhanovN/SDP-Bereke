from django.db import models

class UploadedP12(models.Model):
    filename = models.CharField(max_length=255)
    file_data = models.BinaryField()  # содержимое псевдо-p12 файла
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Сертификат'
        verbose_name_plural = 'Сертификаты'

    def __str__(self):
        return self.filename