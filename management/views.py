from django.shortcuts import render, redirect, get_object_or_404

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from accounts.models import Profile
from universities.models import University
from challenges.models import Challenge, Submission
from django.core.mail import send_mail, send_mass_mail
from django.conf import settings as django_settings
from notifications.models import Notification


User = get_user_model()


# ─── Access control decorators ───────────────────────────────────────────────

def super_admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.user_type != 'super_admin':
            messages.error(request, 'Access denied.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or request.user.user_type not in ('campus_admin', 'super_admin'):
            messages.error(request, 'Access denied.')
            return redirect('dashboard:home')
        return view_func(request, *args, **kwargs)
    wrapper.__name__ = view_func.__name__
    return wrapper


# ─── Super Admin Views ────────────────────────────────────────────────────────

@login_required
@super_admin_required
def super_dashboard(request):
    context = {
        'total_universities': University.objects.filter(is_active=True).count(),
        'total_students': User.objects.filter(user_type='student').count(),
        'total_admins': User.objects.filter(user_type='campus_admin').count(),
        'total_submissions': Submission.objects.count(),
        'passed_submissions': Submission.objects.filter(status='passed').count(),
        'universities': University.objects.all(),
    }
    return render(request, 'management/super_dashboard.html', context)


@login_required
@super_admin_required
def university_list(request):
    universities = University.objects.all()
    return render(request, 'management/university_list.html', {'universities': universities})


@login_required
@super_admin_required
def university_create(request):
    from universities.forms import UniversityForm
    if request.method == 'POST':
        form = UniversityForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'University added.')
            return redirect('management:university_list')
    else:
        form = UniversityForm()
    return render(request, 'management/university_form.html', {'form': form, 'action': 'Add'})


@login_required
@super_admin_required
def university_edit(request, pk):
    from universities.forms import UniversityForm
    university = get_object_or_404(University, pk=pk)
    if request.method == 'POST':
        form = UniversityForm(request.POST, request.FILES, instance=university)
        if form.is_valid():
            form.save()
            messages.success(request, 'University updated.')
            return redirect('management:university_list')
    else:
        form = UniversityForm(instance=university)
    return render(request, 'management/university_form.html', {'form': form, 'action': 'Edit'})


@login_required
@super_admin_required
def create_campus_admin(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        university_id = request.POST.get('university')

        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
        else:
            university = get_object_or_404(University, pk=university_id)
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                user_type='campus_admin'
            )
            Profile.objects.get_or_create(user=user)
            user.profile.university = university
            user.profile.onboarding_complete = True
            user.profile.save()
            messages.success(request, f'Campus admin {username} created for {university.name}.')
            return redirect('management:admin_list')

    universities = University.objects.filter(is_active=True)
    return render(request, 'management/create_campus_admin.html', {'universities': universities})


@login_required
@super_admin_required
def admin_list(request):
    admins = User.objects.filter(user_type='campus_admin').select_related('profile__university')
    return render(request, 'management/admin_list.html', {'admins': admins})


@login_required
@super_admin_required
def all_students(request):
    students = User.objects.filter(user_type='student').select_related('profile__university')
    return render(request, 'management/student_list.html', {'students': students, 'scope': 'all'})


# ─── Campus Admin Views ───────────────────────────────────────────────────────

@login_required
@admin_required
def campus_dashboard(request):
    university = request.user.profile.university

    # super_admin sees everything, campus_admin sees their campus only
    if request.user.user_type == 'super_admin':
        students = User.objects.filter(user_type='student')
        submissions = Submission.objects.all()
        challenges = Challenge.objects.all()
    else:
        students = User.objects.filter(user_type='student', profile__university=university)
        submissions = Submission.objects.filter(student__profile__university=university)
        challenges = Challenge.objects.filter(created_by__profile__university=university)

    context = {
        'university': university,
        'total_students': students.count(),
        'pending_submissions': submissions.filter(status='pending').count(),
        'passed_submissions': submissions.filter(status='passed').count(),
        'total_challenges': challenges.count(),
        'recent_submissions': submissions.order_by('-submitted_at')[:10],
    }
    return render(request, 'management/campus_dashboard.html', context)


@login_required
@admin_required
def campus_students(request):
    if request.user.user_type == 'super_admin':
        students = User.objects.filter(user_type='student').select_related('profile__university')
    else:
        students = User.objects.filter(
            user_type='student',
            profile__university=request.user.profile.university
        ).select_related('profile')

    return render(request, 'management/student_list.html', {'students': students, 'scope': 'campus'})


@login_required
@admin_required
def challenge_create(request):
    from challenges.forms import ChallengeForm
    if request.method == 'POST':
        form = ChallengeForm(request.POST)
        if form.is_valid():
            challenge = form.save(commit=False)
            challenge.created_by = request.user
            challenge.save()

            _notify_students_new_challenge(challenge)

            messages.success(request, 'Challenge created.')
            return redirect('challenges:list')
    else:
        form = ChallengeForm()
    return render(request, 'management/challenge_form.html', {'form': form, 'action': 'Create'})

@login_required
@admin_required
def challenge_edit(request, pk):
    from challenges.forms import ChallengeForm
    challenge = get_object_or_404(Challenge, pk=pk)

    # campus_admin can only edit their own challenges
    if request.user.user_type == 'campus_admin' and challenge.created_by != request.user:
        messages.error(request, 'You can only edit your own challenges.')
        return redirect('challenges:list')

    if request.method == 'POST':
        form = ChallengeForm(request.POST, instance=challenge)
        if form.is_valid():
            form.save()
            messages.success(request, 'Challenge updated.')
            return redirect('challenges:list')
    else:
        form = ChallengeForm(instance=challenge)
    return render(request, 'management/challenge_form.html', {'form': form, 'action': 'Edit'})

@login_required
@super_admin_required
def change_user_role(request, pk):
    target_user = get_object_or_404(User, pk=pk)

    # Prevent super_admin from demoting themselves
    if target_user == request.user:
        messages.error(request, "You can't change your own role.")
        return redirect('management:all_students')

    if request.method == 'POST':
        new_role = request.POST.get('user_type')
        if new_role in ('student', 'campus_admin', 'super_admin'):
            old_role = target_user.user_type
            target_user.user_type = new_role
            target_user.save()

            # If promoted to campus_admin, make sure they have a profile
            Profile.objects.get_or_create(user=target_user)

            messages.success(request, f'{target_user.username} changed from {old_role} to {new_role}.')
        else:
            messages.error(request, 'Invalid role.')
        return redirect('management:all_students')

    return render(request, 'management/change_role.html', {'target_user': target_user})

@login_required
@super_admin_required
def employer_list(request):
    from accounts.models import EmployerProfile
    employers = EmployerProfile.objects.select_related('user').all()
    return render(request, 'management/employer_list.html', {'employers': employers})


@login_required
@super_admin_required
def verify_employer(request, pk):
    from accounts.models import EmployerProfile
    employer_profile = get_object_or_404(EmployerProfile, pk=pk)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'verify':
            employer_profile.is_verified = True
            employer_profile.save()
            messages.success(
                request,
                f'{employer_profile.company_name} verified successfully.'
            )
        elif action == 'reject':
            employer_profile.user.delete()
            messages.success(request, 'Employer account rejected and removed.')
            return redirect('management:employer_list')

    return redirect('management:employer_list')


@login_required
@admin_required
def employer_interests(request):
    from challenges.models import EmployerInterest
    if request.user.user_type == 'super_admin':
        interests = EmployerInterest.objects.select_related(
            'employer__employer_profile', 'student__profile'
        ).all()
    else:
        interests = EmployerInterest.objects.filter(
            student__profile__university=request.user.profile.university
        ).select_related('employer__employer_profile', 'student__profile')

    if request.method == 'POST':
        interest_id = request.POST.get('interest_id')
        from challenges.models import EmployerInterest
        interest = get_object_or_404(EmployerInterest, pk=interest_id)
        interest.status = 'forwarded'
        interest.save()

        # Notify student
        from notifications.models import Notification
        Notification.objects.create(
            recipient=interest.student,
            message=(
                f'{interest.employer.employer_profile.company_name} has expressed '
                f'interest in you for a {interest.get_job_type_display()} opportunity. '
                f'Your campus admin will be in touch.'
            ),
            notification_type='general',
            link='/accounts/profile/'
        )
        messages.success(request, 'Interest forwarded to student.')
        return redirect('management:employer_interests')

    return render(request, 'management/employer_interests.html', {'interests': interests})

def _notify_students_new_challenge(challenge):
    """
    Notify all students whose discipline matches the challenge
    and who have opted in to new challenge notifications.
    """
    from django.contrib.auth import get_user_model
    from notifications.models import Notification
    from django.core.mail import send_mail
    from django.conf import settings as django_settings

    User = get_user_model()

    # Get eligible students — matching discipline, opt-in enabled
    eligible_students = User.objects.filter(
        user_type='student',
        profile__discipline=challenge.discipline,
        profile__notify_on_new_challenge=True,
    ).select_related('profile')

    # In-platform notifications (bulk create — one DB hit)
    notifications = [
        Notification(
            recipient=student,
            message=(
                f'New {challenge.get_difficulty_display()} challenge: '
                f'"{challenge.title}" — {challenge.points} pts'
            ),
            notification_type='new_challenge',
            link=f'/challenges/{challenge.pk}/'
        )
        for student in eligible_students
    ]
    Notification.objects.bulk_create(notifications)

    # Email notifications — only students with email, respect personal_email preference
    email_messages = []
    for student in eligible_students:
        recipient_email = (
            student.profile.personal_email or student.email
        )
        if not recipient_email:
            continue

        email_messages.append((
            f'ConnectED — New Challenge: {challenge.title}',
            (
                f'Hi {student.username},\n\n'
                f'A new challenge has been posted in your discipline '
                f'({challenge.get_discipline_display()}).\n\n'
                f'Challenge: {challenge.title}\n'
                f'Difficulty: {challenge.get_difficulty_display()}\n'
                f'Points: {challenge.points}\n'
                f'Min Year: Year {challenge.min_year}+\n'
                + (f'Deadline: {challenge.deadline.strftime("%d %b %Y %H:%M")}\n' if challenge.deadline else '')
                + f'\nView it at: /challenges/{challenge.pk}/\n\n'
                f'— The ConnectED Team\n\n'
                f'To stop these emails, update your notification preferences in Settings.'
            ),
            django_settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
        ))

    if email_messages:
        from django.core.mail import send_mass_mail
        try:
            send_mass_mail(email_messages, fail_silently=True)
        except Exception:
            pass  # Never crash challenge creation because email failed