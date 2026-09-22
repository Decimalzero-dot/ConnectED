from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.urls import reverse_lazy, reverse
from django.db import IntegrityError
from django_ratelimit.decorators import ratelimit
from .models import User, Profile, EmployerProfile
from .forms import UserRegistrationForm, UserLoginForm, StudentProfileForm, AdminProfileForm, EmployerRegistrationForm
from notifications.models import Notification
from django.core.mail import send_mail
from django.conf import settings as django_settings
from .settings_forms import (
    AccountSettingsForm, AcademicSettingsForm,
    AppearanceSettingsForm, NotificationSettingsForm,
    PasswordChangeSettingsForm, EmployerProfileForm
)


@ratelimit(key='ip', rate='3/m', method='POST', block=True)
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
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


@ratelimit(key='ip', rate='5/m', method='POST', block=True)
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


def handler429(request, exception=None):
    return render(request, 'errors/429.html', status=429)


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
    profile = request.user.profile

    if request.user.user_type == 'student':
        FormClass = StudentProfileForm
    else:
        FormClass = AdminProfileForm

    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            if request.user.user_type == 'student':
                reg_number = form.cleaned_data.get('reg_number')
                if reg_number:
                    profile.reg_number = reg_number
                    profile.save()
            messages.success(request, 'Profile updated.')
            return redirect('accounts:profile')
    else:
        initial = {}
        if request.user.user_type == 'student':
            initial['reg_number'] = profile.reg_number
        form = FormClass(instance=request.user, initial=initial)

    return render(request, 'accounts/profile.html', {
        'form': form,
        'profile': profile,
    })


@login_required
def settings_view(request):
    user = request.user
    profile, _ = Profile.objects.get_or_create(user=user)

    account_form = AccountSettingsForm(instance=user)
    academic_form = AcademicSettingsForm(instance=profile)
    appearance_form = AppearanceSettingsForm(instance=profile)
    notification_form = NotificationSettingsForm(instance=profile)
    password_form = PasswordChangeSettingsForm()

    active_tab = 'account'
    employer_form = None
    if user.user_type == 'employer':
        try:
            employer_form = EmployerProfileForm(instance=user.employer_profile)
        except EmployerProfile.DoesNotExist:
            employer_form = EmployerProfileForm()

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
                return redirect(f"{reverse('accounts:settings')}?tab=account")

                   

        elif tab == 'employer':
            try:
                employer_form = EmployerProfileForm(
                    request.POST,
                    instance=user.employer_profile
                )
            except EmployerProfile.DoesNotExist:
                employer_form = EmployerProfileForm(request.POST)

            if employer_form.is_valid():
                emp_profile = employer_form.save(commit=False)
                emp_profile.user = user
                emp_profile.save()
                messages.success(request, 'Company information updated.')
                return redirect(f"{reverse('accounts:settings')}?tab=employer")

        elif tab == 'academic':
            academic_form = AcademicSettingsForm(request.POST, instance=profile)
            if academic_form.is_valid():
                academic_form.save()
                messages.success(request, 'Academic info updated.')
                return redirect(f"{reverse('accounts:settings')}?tab=academic")

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
                return redirect(f"{reverse('accounts:settings')}?tab=notifications")

        elif tab == 'security':
            password_form = PasswordChangeSettingsForm(request.POST)
            if password_form.is_valid():
                current = password_form.cleaned_data['current_password']
                new_password = password_form.cleaned_data['new_password']
                if user.check_password(current):
                    user.set_password(new_password)
                    user.save()
                    update_session_auth_hash(request, user)
                    messages.success(request, 'Password changed successfully.')
                    return redirect(f"{reverse('accounts:settings')}?tab=security")
                else:
                    password_form.add_error('current_password', 'Current password is incorrect.')

    active_tab = request.GET.get('tab', active_tab)

    context = {
        'account_form': account_form,
        'academic_form': academic_form,
        'appearance_form': appearance_form,
        'notification_form': notification_form,
        'password_form': password_form,
        'active_tab': active_tab,
        'profile': profile,
        'employer_form': employer_form,
    }
    return render(request, 'accounts/settings.html', context)


@ratelimit(key='ip', rate='3/m', method='POST', block=True)
def employer_register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = EmployerRegistrationForm(request.POST)

        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.user_type = 'employer'
                user.save()

                EmployerProfile.objects.create(
                    user=user,
                    company_name=form.cleaned_data['company_name'],
                    company_email=form.cleaned_data['email'],
                    company_website=form.cleaned_data.get('company_website', ''),
                    industry=form.cleaned_data.get('industry', ''),
                    is_verified=False,
                )

                super_admins = User.objects.filter(user_type='super_admin')

                for sa in super_admins:
                    Notification.objects.create(
                        recipient=sa,
                        message=(
                            f'New employer registration: '
                            f'{form.cleaned_data["company_name"]} — awaiting verification.'
                        ),
                        notification_type='general',
                        link='/management/employers/',
                    )

                super_admin_emails = [sa.email for sa in super_admins if sa.email]

                if super_admin_emails:
                    send_mail(
                        subject='ConnectED — New Employer Registration',
                        message=(
                            'A new employer has registered and is awaiting verification.\n\n'
                            f'Company: {form.cleaned_data["company_name"]}\n'
                            f'Email: {form.cleaned_data["email"]}\n'
                            f'Industry: {form.cleaned_data.get("industry", "Not specified")}\n\n'
                            'Review at: /management/employers/'
                        ),
                        from_email=django_settings.DEFAULT_FROM_EMAIL,
                        recipient_list=super_admin_emails,
                        fail_silently=True,
                    )

                messages.success(
                    request,
                    'Account created. Please wait for admin verification '
                    'before you can access the platform.',
                )
                return redirect('accounts:login')

            except IntegrityError:
                form.add_error('username', 'That username is already taken.')

        messages.error(request, 'Please correct the errors below.')

    else:
        form = EmployerRegistrationForm()

    return render(
        request,
        'accounts/employer_register.html',
        {'form': form},
    )