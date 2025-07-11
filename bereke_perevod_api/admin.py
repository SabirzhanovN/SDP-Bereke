from django.contrib import admin
from django.utils.html import format_html
from .models import UploadedP12

@admin.register(UploadedP12)
class UploadedP12Admin(admin.ModelAdmin):
    list_display = ('id', 'filename', 'uploaded_at', 'file_preview')
    readonly_fields = ('uploaded_at', 'file_preview')
    search_fields = ('filename',)
    ordering = ('-uploaded_at',)

    def file_preview(self, obj):
        # Попытка показать первые 300 символов файла как текст
        try:
            content = obj.file_data.decode('utf-8')
            preview = content[:300]
            if len(content) > 300:
                preview += '...'
            return format_html('<pre style="white-space: pre-wrap; max-height: 300px; overflow: auto;">{}</pre>', preview)
        except Exception:
            return "Cannot decode file content"

    file_preview.short_description = "File Preview"
