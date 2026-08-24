from django.shortcuts import render, redirect

# Create your views here.
from django.contrib.auth import login, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, UserLoginForm, UserProfileForm, StudentProfileForm, AdminProfileForm
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.urls import reverse_lazy, reverse 
from django.db import IntegrityError
from .models import User, Profile
from .settings_forms import (
    AccountSettingsForm, AcademicSettingsForm,
    AppearanceSettingsForm, NotificationSettingsForm,
    PasswordChangeSettingsForm
)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                # Auto-assign university from email domain
                if hasattr(form, 'university'):
                    profile, _ = Profile.objects.get_or_create(user=user)
                    profile.university = form.university
                    profile.save()
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                messages.success(request, 'Account created successfully!')
                return redirect('dashboard:onboarding')
            except IntegrityError:
                form.add_error('username', 'That username is already taken.')
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

@login_required
def settings_view(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)

    # Initialize all forms with current data
    account_form = AccountSettingsForm(instance=user)
    academic_form = AcademicSettingsForm(instance=profile)
    appearance_form = AppearanceSettingsForm(instance=profile)
    notification_form = NotificationSettingsForm(instance=profile)
    password_form = PasswordChangeSettingsForm()

    active_tab = 'account'  # default tab

    if request.method == 'POST':
        tab = request.POST.get('tab')
        active_tab = tab

        if tab == 'account':
            account_form = AccountSettingsForm(
                request.POST, request.FILES, instance=user
            )
            if account_form.is_valid():
                account_form.save()
                messages.success(request, 'Account details updated.')
                return redirect(f'/settings/?tab=account')

        elif tab == 'academic':
            academic_form = AcademicSettingsForm(request.POST, instance=profile)
            if academic_form.is_valid():
                academic_form.save()
                messages.success(request, 'Academic info updated.')
                return redirect(f'/settings/?tab=academic')

        elif tab == 'appearance':
            appearance_form = AppearanceSettingsForm(request.POST, instance=profile)
            if appearance_form.is_valid():
                appearance_form.save()
                messages.success(request, 'Appearance settings saved.')
                return redirect(f"{reverse('accounts:settings')}?tab=appearance")

        elif tab == 'notifications':
            notification_form = NotificationSettingsForm(request.POST, instance=profile)
            if notification_form.is_valid():
                notification_form.save()
                messages.success(request, 'Notification preferences saved.')
                return redirect(f'/settings/?tab=notifications')

        elif tab == 'security':
            password_form = PasswordChangeSettingsForm(request.POST)
            if password_form.is_valid():
                current = password_form.cleaned_data['current_password']
                new_password = password_form.cleaned_data['new_password']
                if user.check_password(current):
                    user.set_password(new_password)
                    user.save()
                    # Keep user logged in after password change
                    update_session_auth_hash(request, user)
                    messages.success(request, 'Password changed successfully.')
                    return redirect('/settings/?tab=security')
                else:
                    password_form.add_error('current_password', 'Current password is incorrect.')

    # Read active tab from GET param (after redirect)
    active_tab = request.GET.get('tab', active_tab)

    context = {
        'account_form': account_form,
        'academic_form': academic_form,
        'appearance_form': appearance_form,
        'notification_form': notification_form,
        'password_form': password_form,
        'active_tab': active_tab,
        'profile': profile,
    }
    return render(request, 'accounts/settings.html', context)
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

            # Save reg_number for students only
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