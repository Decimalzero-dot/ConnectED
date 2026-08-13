from django.shortcuts import render, redirect

# Create your views here.
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm, StudentProfileForm, AdminProfileForm
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.urls import reverse_lazy
from django.db import IntegrityError

def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, 'Account created successfully!')
                return redirect('dashboard:onboarding')
            except IntegrityError:
                form.add_error('username', 'That username is already taken. Please choose another.')
        messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('dashboard:home')
        messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()

    return render(request, 'accounts/login.html', {'form': form})


@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)

    return render(request, 'accounts/profile.html', {'form': form})


class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')

@login_required
def profile_view(request):
    if request.user.user_type == 'student':
        FormClass = StudentProfileForm
    else:
        FormClass = AdminProfileForm

    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated.')
            return redirect('accounts:profile')
    else:
        form = FormClass(instance=request.user)

    return render(request, 'accounts/profile.html', {'form': form})    
@login_required
def profile_view(request):
    profile = request.user.profile

    if request.user.user_type == 'student':
        FormClass = StudentProfileForm
    else:
        FormClass = AdminProfileForm

    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()

            # Save reg_number to Profile separately (students only)
            if request.user.user_type == 'student':
                reg_number = form.cleaned_data.get('reg_number')
                if reg_number:
                    profile.reg_number = reg_number
                    profile.save()

            messages.success(request, 'Profile updated.')
            return redirect('accounts:profile')
    else:
        # Pre-fill reg_number from existing profile
        initial = {}
        if request.user.user_type == 'student':
            initial['reg_number'] = profile.reg_number
        form = FormClass(instance=request.user, initial=initial)

    return render(request, 'accounts/profile.html', {
        'form': form,
        'profile': profile,
    })