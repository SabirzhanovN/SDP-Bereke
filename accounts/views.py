from django.shortcuts import render


def login(request):
    if request.method == 'POST':
        pass
    return render(request, 'accounts/login.html')