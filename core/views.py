from django.shortcuts import render, redirect

# Create your views here.

def landing_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    return render(request, 'core/landing.html')