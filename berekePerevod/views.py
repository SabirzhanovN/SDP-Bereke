import requests
from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse

from django.contrib.auth.decorators import login_required

from bereke_perevod_api.models import UploadedP12


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

        api_url = request.build_absolute_uri(reverse('file-create'))

        try:
            session_id = request.COOKIES.get('sessionid')
            response = requests.post(api_url, json=data, cookies={'sessionid': session_id})
            if response.status_code == 201:
                messages.success(request, "Сертификат успешно создан!")
                return redirect('home')
            else:
                messages.error(request, f"Ошибка: {response.json()}")
        except requests.RequestException:
            messages.error(request, "Ошибка соединения с API")


    return render(request, 'berekePerevod/index.html')


@login_required
def detail(request):
    page = int(request.GET.get('page', '1'))
    search_query = request.GET.get('search', '').strip()
    date_filter = request.GET.get('date', '').strip()

    relative_url = reverse('files')
    api_url = request.build_absolute_uri(relative_url)

    params = {'page': page}
    if search_query:
        params['search'] = search_query
    if date_filter:
        params['date'] = date_filter

    try:
        session_id = request.COOKIES.get('sessionid')
        response = requests.get(api_url, params=params, cookies={'sessionid': session_id})
        if response.status_code == 200:
            data = response.json()
            files = data.get('results', [])
            count = int(data.get('count', 0))
            page_size = settings.REST_FRAMEWORK.get('PAGE_SIZE', 5)
            total_pages = (count + page_size - 1) // page_size
        else:
            files, page, total_pages = [], 1, 1
    except Exception as e:
        files, page, total_pages = [], 1, 1

    return render(request, 'berekePerevod/view.html', {
        'files': files,
        'current_page': page,
        'total_pages': total_pages,
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
