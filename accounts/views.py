from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, authenticate, update_session_auth_hash, get_user_model
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
from django.http import Http404, JsonResponse
from django.views.decorators.http import require_POST
from .settings_forms import (
    AccountSettingsForm, AcademicSettingsForm,
    AppearanceSettingsForm, NotificationSettingsForm,
    PasswordChangeSettingsForm, EmployerProfileForm
)
import re
import secrets
import requests
from universities.models import University
from .google_auth import build_auth_url, exchange_code
from django.utils.http import url_has_allowed_host_and_scheme
from urllib.parse import urlencode
from django.conf import settings

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
                next_url = _safe_next(request)
                if next_url:
                    return redirect(next_url)
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

def portfolio_view(request, username):
    from challenges.models import Submission

    User = get_user_model()
    student = get_object_or_404(User, username=username, user_type='student')
    profile = get_object_or_404(Profile, user=student)

    # Privacy check
    # Owners always see their own portfolio
    # Others only see it if portfolio_public = True
    is_owner = request.user.is_authenticated and request.user == student
    is_admin = request.user.is_authenticated and request.user.user_type in ('campus_admin', 'super_admin')
    is_employer = request.user.is_authenticated and request.user.user_type == 'employer'

    if not profile.portfolio_public and not is_owner and not is_admin:
        raise Http404

    # Get passed submissions — ordered by most recent
    passed_submissions = Submission.objects.filter(
        student=student,
        status='passed'
    ).select_related('challenge').order_by('-reviewed_at')

    # Stats
    total_points = sum(s.score or s.challenge.points for s in passed_submissions)
    disciplines_covered = list(
        passed_submissions.values_list(
            'challenge__discipline', flat=True
        ).distinct()
    )

    context = {
        'student': student,
        'profile': profile,
        'passed_submissions': passed_submissions,
        'total_points': total_points,
        'total_completed': passed_submissions.count(),
        'disciplines_covered': disciplines_covered,
        'is_owner': is_owner,
        'is_employer': is_employer,
        'can_express_interest': (
            is_employer and
            hasattr(request.user, 'employer_profile') and
            request.user.employer_profile.is_verified
        ),
    }
    return render(request, 'accounts/portfolio.html', context)

@login_required
@require_POST
def toggle_dark_mode(request):
    profile, _ = Profile.objects.get_or_create(user=request.user)
    profile.dark_mode = not profile.dark_mode
    profile.save(update_fields=['dark_mode'])
    return JsonResponse({'dark_mode': profile.dark_mode})

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
@login_required
def github_connect(request):
    academic_url = f"{reverse('accounts:settings')}?tab=academic"
    if request.user.user_type != 'student' or not settings.GITHUB_CLIENT_ID:
        messages.error(request, 'GitHub sign-in is not available.')
        return redirect(academic_url)

    state = secrets.token_urlsafe(32)
    request.session['github_oauth_state'] = state
    params = {
        'client_id': settings.GITHUB_CLIENT_ID,
        'redirect_uri': f"{settings.SITE_URL}{reverse('accounts:github_callback')}",
        'state': state,
        'allow_signup': 'false',
    }
    return redirect(f"https://github.com/login/oauth/authorize?{urlencode(params)}")


@login_required
def github_callback(request):
    academic_url = f"{reverse('accounts:settings')}?tab=academic"

    # CSRF protection: the state we sent must come back unchanged
    expected = request.session.pop('github_oauth_state', None)
    returned = request.GET.get('state', '')
    if not expected or not secrets.compare_digest(expected, returned):
        messages.error(request, 'GitHub sign-in could not be verified. Please try again.')
        return redirect(academic_url)

    code = request.GET.get('code')
    if not code:  # student clicked "Cancel" on GitHub
        messages.info(request, 'GitHub connection was cancelled.')
        return redirect(academic_url)

    try:
        token = requests.post(
            'https://github.com/login/oauth/access_token',
            data={
                'client_id': settings.GITHUB_CLIENT_ID,
                'client_secret': settings.GITHUB_CLIENT_SECRET,
                'code': code,
                'redirect_uri': f"{settings.SITE_URL}{reverse('accounts:github_callback')}",
            },
            headers={'Accept': 'application/json'},
            timeout=10,
        ).json().get('access_token')
        if not token:
            raise ValueError('no access token')

        gh = requests.get(
            'https://api.github.com/user',
            headers={'Authorization': f'Bearer {token}',
                     'Accept': 'application/vnd.github+json'},
            timeout=10,
        ).json()
        gh_id, gh_login = gh['id'], gh['login']
    except (requests.RequestException, ValueError, KeyError):
        messages.error(request, 'Could not complete GitHub sign-in. Please try again.')
        return redirect(academic_url)

    profile, _ = Profile.objects.get_or_create(user=request.user)

    if Profile.objects.filter(github_id=gh_id).exclude(pk=profile.pk).exists():
        messages.error(request, f'@{gh_login} is already linked to another ConnectED account.')
        return redirect(academic_url)

    profile.github_id = gh_id
    profile.github_username = gh_login
    profile.github_verified = True
    profile.save()
    messages.success(request, f'GitHub account @{gh_login} verified.')
    return redirect(academic_url)

def _safe_next(request):
    nxt = request.GET.get('next') or request.POST.get('next')
    if nxt and url_has_allowed_host_and_scheme(
        nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return nxt
    return None

@ratelimit(key='ip', rate='10/m', method='GET', block=True)
def google_login(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    if not settings.GOOGLE_CLIENT_ID:
        messages.error(request, 'Google sign-in is not available right now.')
        return redirect('accounts:login')

    state, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    request.session['google_oauth'] = {'state': state, 'nonce': nonce}
    return redirect(build_auth_url(state, nonce))


def _google_student(claims, email, university):
    """Returns (user, error_message). Never links into staff accounts."""
    sub = claims['sub']

    profile = Profile.objects.filter(google_sub=sub).select_related('user').first()
    if profile:
        return profile.user, None

    matches = User.objects.filter(email__iexact=email)
    if matches.exclude(user_type='student').exists():
        return None, 'That email belongs to a staff account. Please log in with your password.'

    user = matches.first()
    if user:
        # Google just proved this person owns the mailbox. Password sign-up never
        # verified emails, so wipe any password set by whoever registered it first.
        user.set_unusable_password()
        user.save(update_fields=['password'])
    else:
        base = re.sub(r'[^A-Za-z0-9_.-]', '', email.split('@')[0])[:30] or 'student'
        username, n = base, 1
        while User.objects.filter(username__iexact=username).exists():
            n += 1
            username = f'{base}{n}'
        user = User.objects.create_user(
            username=username,
            email=email,
            first_name=claims.get('given_name', '')[:150],
            last_name=claims.get('family_name', '')[:150],
            user_type='student',
        )

    profile, _ = Profile.objects.get_or_create(user=user)
    profile.university = university
    profile.google_sub = sub
    profile.save()
    return user, None


def google_callback(request):
    saved = request.session.pop('google_oauth', None)
    if not saved or not secrets.compare_digest(saved['state'], request.GET.get('state', '')):
        messages.error(request, 'Google sign-in could not be verified. Please try again.')
        return redirect('accounts:login')

    code = request.GET.get('code')
    if not code:  # student pressed Cancel on Google's screen
        messages.info(request, 'Google sign-in was cancelled.')
        return redirect('accounts:login')

    try:
        claims = exchange_code(code)
    except (ValueError, requests.RequestException):
        messages.error(request, 'Could not complete Google sign-in. Please try again.')
        return redirect('accounts:login')

    if not secrets.compare_digest(str(claims.get('nonce', '')), saved['nonce']):
        messages.error(request, 'Google sign-in could not be verified. Please try again.')
        return redirect('accounts:login')

    email = claims['email'].lower()
    domain = email.rsplit('@', 1)[-1]
    university = University.objects.filter(email_domain__iexact=domain, is_active=True).first()
    if not university:
        messages.error(request, 'Please use your university Google account. '
                                'That email domain is not on ConnectED yet.')
        return redirect('accounts:login')

    user, error = _google_student(claims, email, university)
    if error:
        messages.error(request, error)
        return redirect('accounts:login')
    if not user.is_active:
        messages.error(request, 'This account has been deactivated.')
        return redirect('accounts:login')

    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
    return redirect('dashboard:home')  # new students get sent on to onboarding