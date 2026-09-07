from django.shortcuts import render, get_object_or_404, redirect

# Create your views here.
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Challenge, Submission, EmployerInterest
from .forms import SubmissionForm, ChallengeForm, EmployerInterestForm
from django.utils import timezone
from notifications.models import Notification
from django.core.mail import send_mail
from django.conf import settings as django_settings


@login_required
def challenge_list(request):
    challenges = Challenge.objects.filter(is_active=True)
    profile = request.user.profile

    # Optional filter by discipline via query param
    discipline_filter = request.GET.get('discipline')
    if discipline_filter:
        challenges = challenges.filter(discipline=discipline_filter)

    # Annotate eligibility for template display
    challenge_data = []
    for challenge in challenges:
        challenge_data.append({
            'challenge': challenge,
            'eligible': challenge.is_eligible_for(profile),
        })

    context = {
        'challenge_data': challenge_data,
        'discipline_choices': Challenge.DISCIPLINE_CHOICES,
        'selected_discipline': discipline_filter,
    }
    return render(request, 'challenges/challenge_list.html', context)


@login_required
def challenge_detail(request, pk):
    challenge = get_object_or_404(Challenge, pk=pk, is_active=True)
    profile = request.user.profile
    eligible = challenge.is_eligible_for(profile)

    # Get's student's latest submission
    submission = Submission.objects.filter(challenge=challenge, student=request.user).first()

    form = None
    if eligible and request.method == 'POST':
        form = SubmissionForm(request.POST)
        if form.is_valid():
            new_submission = form.save(commit=False)
            new_submission.challenge = challenge
            new_submission.student = request.user
            new_submission.save()
            messages.success(request, 'Submission received! Awaiting review.')
            return redirect('challenges:detail', pk=challenge.pk)
    elif eligible:
        form = SubmissionForm()

    context = {
        'challenge': challenge,
        'eligible': eligible,
        'submission': submission,
        'form': form,
    }
    return render(request, 'challenges/challenge_detail.html', context)


def is_reviewer(user):
    return user.is_authenticated and user.user_type in ('campus_admin', 'super_admin')


@login_required
@user_passes_test(is_reviewer)
def review_queue(request):
    submissions = Submission.objects.filter(status='pending').select_related('student__profile', 'challenge')

    if request.user.user_type == 'campus_admin':
        submissions = submissions.filter(student__profile__university=request.user.profile.university)

    return render(request, 'challenges/review_queue.html', {'submissions': submissions})


@login_required
@user_passes_test(is_reviewer)
def review_submission(request, pk):
    submission = get_object_or_404(Submission, pk=pk)

    # Campus admin review's their own campus's submissions
    if request.user.user_type == 'campus_admin':
        if submission.student.profile.university != request.user.profile.university:
            messages.error(request, "You can only review submissions from your own campus.")
            return redirect('challenges:review_queue')

    if request.method == 'POST':
        decision = request.POST.get('decision')
        feedback = request.POST.get('feedback', '')

        if decision in ('passed', 'failed'):
            submission.status = decision
            submission.feedback = feedback
            submission.reviewed_at = timezone.now()
            submission.save()
            Notification.objects.create(
            recipient=submission.student,
            message=f'Your submission for "{submission.challenge.title}" was marked {decision}.',
            notification_type='submission_reviewed',
            link=f'/challenges/{submission.challenge.pk}/'
            )
            if submission.student.profile.notify_on_review:
                send_mail(
                    subject=f'ConnectED — Submission {decision.title()}',
                    message=(
                        f'Hi {submission.student.username},\n\n'
                        f'Your submission for "{submission.challenge.title}" has been marked {decision}.\n\n'
                        f'{"Feedback: " + submission.feedback if submission.feedback else ""}\n\n'
                        f'Visit ConnectED to view your updated leaderboard rank.\n\n'
                        f'— The ConnectED Team'
                    ),
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[submission.student.email],
                    fail_silently=True,  # doesn't crash the review if email fails
                )
            messages.success(request, f'Submission marked as {decision}.')
            return redirect('challenges:review_queue')

    return render(request, 'challenges/review_submission.html', {'submission': submission})


def is_verified_employer(user):
    return (
        user.is_authenticated and
        user.user_type == 'employer' and
        hasattr(user, 'employer_profile') and
        user.employer_profile.is_verified
    )


@login_required
@user_passes_test(is_verified_employer)
def express_interest(request, student_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()

    student = get_object_or_404(User, pk=student_id, user_type='student')

    # Check if already expressed interest
    existing = EmployerInterest.objects.filter(
        employer=request.user,
        student=student
    ).first()

    if existing:
        messages.info(request, 'You have already expressed interest in this student.')
        return redirect('dashboard:leaderboard')

    if request.method == 'POST':
        form = EmployerInterestForm(request.POST)
        if form.is_valid():
            interest = form.save(commit=False)
            interest.employer = request.user
            interest.student = student
            interest.save()

            # Notify campus admin via email
            campus_admins = User.objects.filter(
                user_type='campus_admin',
                profile__university=student.profile.university
            ).select_related('profile')

            admin_emails = [a.email for a in campus_admins if a.email]

            if admin_emails:
                send_mail(
                    subject=f'ConnectED — Employer Interest in {student.username}',
                    message=(
                        f'An employer has expressed interest in one of your students.\n\n'
                        f'Student: {student.username} ({student.email})\n'
                        f'Company: {request.user.employer_profile.company_name}\n'
                        f'Contact: {request.user.employer_profile.company_email}\n'
                        f'Opportunity type: {interest.get_job_type_display()}\n\n'
                        f'Message:\n{interest.message}\n\n'
                        f'Please facilitate the introduction via ConnectED admin panel.'
                    ),
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    fail_silently=True,
                )

            # In-platform notification to campus admin
            from notifications.models import Notification
            for admin in campus_admins:
                Notification.objects.create(
                    recipient=admin,
                    message=(
                        f'{request.user.employer_profile.company_name} expressed '
                        f'interest in {student.username} '
                        f'({interest.get_job_type_display()})'
                    ),
                    notification_type='general',
                    link=f'/management/employer-interests/'
                )

            messages.success(
                request,
                'Interest submitted. The university will facilitate the introduction.'
            )
            return redirect('dashboard:public_leaderboard')
    else:
        form = EmployerInterestForm()

    return render(request, 'challenges/express_interest.html', {
        'form': form,
        'student': student,
    })
@login_required
def sponsor_challenge_view(request):
    if request.user.user_type != 'employer':
        messages.error(request, 'Only employers can sponsor challenges.')
        return redirect('dashboard:home')

    # For now show existing active challenges with a sponsorship CTA
    challenges = Challenge.objects.filter(is_active=True)
    return render(request, 'challenges/sponsor_challenges.html', {
        'challenges': challenges,
    })