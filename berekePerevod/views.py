from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, redirect

from django.contrib.auth.decorators import login_required
from django.utils.dateparse import parse_date

from bereke_perevod_api.models import UploadedP12
from bereke_perevod_api.serializers import CertCreateSerializer


@login_required
def index(request):
    if request.method == 'POST':
        data = {
            "filename": request.POST.get('filename'),
            "expiration": int(request.POST.get('expiration', 365)),
            "password": request.POST.get('password'),
            "password2": request.POST.get('password2'),
            "full_name": request.POST.get('full_name'),
            "department": request.POST.get('department'),
            "organization": request.POST.get('organization'),
            "city": request.POST.get('city'),
            "region": request.POST.get('region'),
            "country_code": request.POST.get('country_code'),
        }

        serializer = CertCreateSerializer(data=data)

        if serializer.is_valid():
            serializer.save()
            messages.success(request, "Сертификат успешно создан!")
            return redirect('home')
        else:
            # Вывод ошибок сериализатора
            for field, errors in serializer.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

    return render(request, 'berekePerevod/index.html')


@login_required
def detail(request):
    page = int(request.GET.get('page', '1'))
    search_query = request.GET.get('search', '').strip()
    date_filter = request.GET.get('date', '').strip()

    queryset = UploadedP12.objects.all()

    # Поиск по имени файла (с учётом символов - _ . и пробелов)
    if search_query:
        import re
        normalized_search = re.sub(r'[-_.]', ' ', search_query).lower()
        queryset = queryset.filter(
            Q(filename__icontains=search_query) |
            Q(filename__icontains=normalized_search)
        )

    # Фильтрация по дате загрузки
    if date_filter:
        parsed_date = parse_date(date_filter)
        if parsed_date:
            queryset = queryset.filter(uploaded_at__date=parsed_date)

    queryset = queryset.order_by('-uploaded_at')

    # Пагинация
    page_size = 5
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    return render(request, 'berekePerevod/view.html', {
        'files': page_obj.object_list,
        'current_page': page_obj.number,
        'total_pages': paginator.num_pages,
        'search': search_query,
        'date': date_filter,
    })


@login_required
def delete(request, pk):
    try:
        file_obj = UploadedP12.objects.get(pk=pk)
        file_obj.delete()
        messages.success(request, 'Файл успешно удалён.')
    except UploadedP12.DoesNotExist:
        messages.error(request, 'Файл не найден.')
    return redirect('detail')
