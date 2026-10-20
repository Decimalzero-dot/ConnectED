from django.shortcuts import render, redirect
from django_ratelimit.exceptions import Ratelimited


# Create your views here.

def landing_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    return render(request, 'core/landing.html')


def error_404(request, exception):
    return render(request, 'errors/404.html', status=404)


def error_500(request):
    return render(request, 'errors/500.html', status=500)


def error_403(request, exception):
    return render(request, 'errors/403.html', status=403)

def privacy_view(request):
    return render(request, 'core/privacy.html')

def error_403(request, exception=None):
    if isinstance(exception, Ratelimited):
        return render(request, 'errors/429.html', status=429)
    return render(request, 'errors/403.html', status=403)