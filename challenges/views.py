from django.shortcuts import render, get_object_or_404, redirect

# Create your views here.
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Challenge, Submission
from .forms import SubmissionForm
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