from urllib.parse import urlencode

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from django.http import FileResponse, Http404
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from notifications.utils import safe_send_mail

from connected import settings
from .models import Challenge, Submission, SubmissionFile, EmployerInterest, SponsorshipInquiry
from .forms import SubmissionForm, ChallengeForm, EmployerInterestForm
from .utils import validate_submission_file
from notifications.models import Notification
from django.core.mail import send_mail
from django.conf import settings as django_settings
from accounts.github import verify_repo
from urllib.parse import urlencode

User = get_user_model()


# ─── Access control ───────────────────────────────────────────────────────────

def is_reviewer(user):
    return user.is_authenticated and user.user_type in ('campus_admin', 'super_admin')


def is_verified_employer(user):
    return (
        user.is_authenticated and
        user.user_type == 'employer' and
        hasattr(user, 'employer_profile') and
        user.employer_profile.is_verified
    )


# ─── Challenge List ───────────────────────────────────────────────────────────

@login_required
def challenge_list(request):
    if request.user.user_type == 'employer':
        return redirect('challenges:sponsor')

    # Auto-deactivate expired
    from django.utils import timezone
    Challenge.objects.filter(
        deadline__lt=timezone.now(),
        is_active=True,
        deadline__isnull=False
    ).update(is_active=False)

    challenges = Challenge.objects.filter(is_active=True)
    profile = request.user.profile

    # Discipline filter is now optional — user can filter if they want
    discipline_filter = request.GET.get('discipline')
    if discipline_filter:
        challenges = challenges.filter(discipline=discipline_filter)

    # Year filter — only show challenges student is eligible for by default
    # but allow them to browse all if they choose
    show_all = request.GET.get('show_all')
    if not show_all and profile.year_of_study:
        challenges = challenges.filter(min_year__lte=profile.year_of_study)

    challenge_data = []
    for challenge in challenges:
        challenge_data.append({
            'challenge': challenge,
            'eligible': challenge.is_eligible_for(profile),
        })

    return render(request, 'challenges/challenge_list.html', {
        'challenge_data': challenge_data,
        'discipline_choices': Challenge.DISCIPLINE_CHOICES,
        'selected_discipline': discipline_filter,
        'show_all': show_all,
        'profile': profile,
    })

# ─── Challenge Detail + Submission ────────────────────────────────────────────

@login_required
def challenge_detail(request, pk):
    challenge = get_object_or_404(Challenge, pk=pk, is_active=True)
    profile = request.user.profile

    eligible = challenge.is_eligible_for(profile)
    lock_reason = ''
    if not eligible:
        lock_reason = (
            'Add your year of study in Settings → Academic Info to unlock challenges.'
            if not profile.year_of_study else
            f'This challenge is for Year {challenge.min_year} and above. '
            f'You are in Year {profile.year_of_study}.'
        )

    # Their most recent attempt (pending, passed or failed)
    latest = (Submission.objects
              .filter(challenge=challenge, student=request.user)
              .order_by('-submitted_at')
              .prefetch_related('files')
              .first())

    # Can submit if: eligible AND (never tried OR last try failed)
    can_submit = eligible and (latest is None or latest.status == 'failed')

    needs_github = bool(
        django_settings.GITHUB_CLIENT_ID
        and challenge.allows_github
        and not profile.github_verified
    )

    form = None
    file_errors = []

    if can_submit and request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.challenge = challenge
            submission.student = request.user
            files = request.FILES.getlist('uploaded_files')

            # Ignore any method this challenge doesn't allow (the form hides them, but POSTs can be edited)
            if not challenge.allows_github:
                submission.github_url = ''
            if not challenge.allows_external_url:
                submission.external_url = ''
            if not challenge.allows_text:
                submission.text_answer = ''
            if not challenge.allows_file_upload:
                files = []

            if not any([submission.github_url, submission.external_url,
                        submission.text_answer, files]):
                form.add_error(None, 'Please provide at least one submission method.')
            else:
                validated_files = []
                for f in files:
                    try:
                        validate_submission_file(f)
                        validated_files.append(f)
                    except ValidationError as e:
                        file_errors.extend(e.messages)

                if submission.github_url:
                    if needs_github:
                        messages.info(request,
                            'To submit a repository, first confirm your GitHub account. '
                            'It takes one tap, then you come straight back here.')
                        return redirect(
                            f"{reverse('accounts:github_connect')}?{urlencode({'next': request.path})}")

                    if not profile.github_username:
                        form.add_error('github_url',
                            'Add your GitHub username in Settings → Academic Info.')
                    else:
                        status, msg, canonical = verify_repo(
                            submission.github_url, profile.github_username)
                        if status == 'fail':
                            form.add_error('github_url', msg)
                        elif status == 'ok':
                            submission.github_url = canonical
                            submission.github_verified = True
                            submission.github_check_summary = msg
                        else:  # GitHub unreachable: don't punish the student
                            submission.github_check_summary = (
                                'Not verified: GitHub could not be reached at submission time.')

                if not file_errors and not form.errors:
                    submission.save()
                    for f in validated_files:
                        SubmissionFile.objects.create(
                            submission=submission, file=f,
                            original_filename=f.name, file_size=f.size)

                    campus_admins = User.objects.filter(
                        user_type='campus_admin', profile__university=profile.university)
                    for admin in campus_admins:
                        Notification.objects.create(
                            recipient=admin,
                            message=f'{request.user.username} submitted "{challenge.title}": awaiting review.',
                            notification_type='general',
                            link=f'/challenges/review/{submission.pk}/')
                    safe_send_mail(
                        subject=f'ConnectED — New Submission: {challenge.title}',
                        message=(f'{request.user.username} submitted "{challenge.title}".\n\n'
                                 f'Review it: {django_settings.SITE_URL}/challenges/review/{submission.pk}/'),
                        recipient_list=[a.email for a in campus_admins])

                    messages.success(request, 'Submission received! Awaiting review.')
                    return redirect('challenges:detail', pk=challenge.pk)

    elif can_submit:
        initial = {}
        if latest:  # retry after a fail: start from what they sent last time
            initial = {'github_url': latest.github_url,
                       'external_url': latest.external_url,
                       'text_answer': latest.text_answer}
        form = SubmissionForm(initial=initial)

    return render(request, 'challenges/challenge_detail.html', {
        'challenge': challenge,
        'eligible': eligible,
        'lock_reason': lock_reason,
        'submission': latest,
        'can_submit': can_submit,
        'form': form,
        'file_errors': file_errors,
        'needs_github': needs_github,
    })

# ─── File Serving ─────────────────────────────────────────────────────────────

@login_required
def serve_submission_file(request, file_id):
    sub_file = get_object_or_404(SubmissionFile, pk=file_id)
    submission = sub_file.submission
    user = request.user

    is_owner = submission.student == user
    is_campus_admin = (
        user.user_type == 'campus_admin' and
        hasattr(user, 'profile') and
        user.profile.university == submission.student.profile.university
    )
    is_super_admin = user.user_type == 'super_admin'

    if not (is_owner or is_campus_admin or is_super_admin):
        raise Http404

    return FileResponse(
        sub_file.file.open('rb'),
        as_attachment=True,
        filename=sub_file.original_filename
    )

@login_required
def serve_submission_file(request, file_id):
    sub_file = get_object_or_404(SubmissionFile, pk=file_id)
    submission = sub_file.submission
    user = request.user

    is_owner = submission.student == user
    is_campus_admin = (
        user.user_type == 'campus_admin' and
        hasattr(user, 'profile') and
        user.profile.university == submission.student.profile.university
    )
    is_super_admin = user.user_type == 'super_admin'

    if not (is_owner or is_campus_admin or is_super_admin):
        raise Http404

    # In production: generate signed URL and redirect
    # In development: serve directly
    if not settings.DEBUG:
        from storages.backends.s3boto3 import S3Boto3Storage
        storage = S3Boto3Storage()
        url = storage.url(sub_file.file.name)
        return redirect(url)
    else:
        return FileResponse(
            sub_file.file.open('rb'),
            as_attachment=True,
            filename=sub_file.original_filename
        )

# ─── Review Queue ─────────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_reviewer)
def review_queue(request):
    submissions = Submission.objects.filter(
        status='pending'
    ).select_related('student__profile', 'challenge')

    if request.user.user_type == 'campus_admin':
        submissions = submissions.filter(
            student__profile__university=request.user.profile.university
        )

    return render(request, 'challenges/review_queue.html', {'submissions': submissions})


# ─── Review Submission ────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_reviewer)
def review_submission(request, pk):
    submission = get_object_or_404(
        Submission.objects
        .select_related('challenge', 'student__profile__university')
        .prefetch_related('files'),
        pk=pk)
    challenge = submission.challenge
    student = submission.student

    if request.user.user_type == 'campus_admin' and \
            student.profile.university != request.user.profile.university:
        messages.error(request, 'You can only review submissions from your own campus.')
        return redirect('challenges:review_queue')

    # Earlier attempts by this student on this challenge (they can retry after a fail)
    previous = list(Submission.objects
                    .filter(challenge=challenge, student=student,
                            submitted_at__lt=submission.submitted_at)
                    .order_by('submitted_at'))

    form_score = submission.score if submission.score is not None else ''
    form_feedback = submission.feedback

    if request.method == 'POST':
        form_score = request.POST.get('score', '').strip()
        form_feedback = request.POST.get('feedback', '').strip()
        decision = request.POST.get('decision')

        errors, score = [], None
        if decision not in ('passed', 'failed'):
            errors.append('Choose Pass or Not passed yet.')
        if len(form_feedback) < 80:
            errors.append('Feedback needs at least 80 characters: say what worked and what to fix.')
        if form_score:
            try:
                score = int(form_score)
                if not 0 <= score <= challenge.points:
                    errors.append(f'Score must be between 0 and {challenge.points}.')
            except ValueError:
                errors.append('Score must be a whole number.')

        if not errors:
            submission.status = decision
            submission.feedback = form_feedback
            submission.score = score
            submission.reviewed_at = timezone.now()
            submission.save()

            label = 'passed' if decision == 'passed' else 'not passed yet'
            Notification.objects.create(
                recipient=student,
                message=(f'Your submission for "{challenge.title}" was marked {label}.'
                         + (f' Score: {score}/{challenge.points}.' if score is not None else '')),
                notification_type='submission_reviewed',
                link=f'/challenges/{challenge.pk}/')

            profile = student.profile
            to = profile.personal_email or student.email
            if profile.notify_on_review and to:
                site = django_settings.SITE_URL
                safe_send_mail(
                    subject=f'ConnectED — {challenge.title}: {label}',
                    message=(
                        f'Hi {student.first_name or student.username},\n\n'
                        f'Your submission for "{challenge.title}" was marked {label}.\n'
                        + (f'Score: {score}/{challenge.points}\n' if score is not None else '')
                        + f'\nFeedback:\n{form_feedback}\n\n'
                        + (f'Fix it and submit again: {site}/challenges/{challenge.pk}/\n\n'
                           if decision == 'failed' else
                           f'See it on your portfolio: {site}/accounts/profile/{student.username}/\n\n')
                        + 'The ConnectED Team'),
                    recipient_list=[to])

            messages.success(request, f'Marked {label}. {student.username} has been notified.')
            return redirect('challenges:review_queue')

        for e in errors:
            messages.error(request, e)

    return render(request, 'challenges/review_submission.html', {
        'submission': submission, 'challenge': challenge, 'student': student,
        'previous': previous, 'attempt_no': len(previous) + 1,
        'form_score': form_score, 'form_feedback': form_feedback,
    })


# ─── Express Interest ─────────────────────────────────────────────────────────

@login_required
@user_passes_test(is_verified_employer)
def express_interest(request, student_id):
    student = get_object_or_404(User, pk=student_id, user_type='student')

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

            campus_admins = User.objects.filter(
                user_type='campus_admin',
                profile__university=student.profile.university
            ).select_related('profile')

            admin_emails = [a.email for a in campus_admins if a.email]
            if admin_emails:
                safe_send_mail(
                    subject=f'ConnectED — Employer Interest in {student.username}',
                    message=(
                        f'An employer has expressed interest in one of your students.\n\n'
                        f'Student: {student.username} ({student.email})\n'
                        f'Company: {request.user.employer_profile.company_name}\n'
                        f'Contact: {request.user.employer_profile.company_email}\n'
                        f'Opportunity: {interest.get_job_type_display()}\n\n'
                        f'Message:\n{interest.message}\n\n'
                        f'Review at: /management/employer-interests/'
                    ),
                    recipient_list=admin_emails,
                )

            for admin in campus_admins:
                Notification.objects.create(
                    recipient=admin,
                    message=(
                        f'{request.user.employer_profile.company_name} expressed '
                        f'interest in {student.username} '
                        f'({interest.get_job_type_display()})'
                    ),
                    notification_type='general',
                    link='/management/employer-interests/'
                )

            messages.success(
                request,
                'Interest submitted. The university will facilitate the introduction.'
            )
            return redirect('dashboard:leaderboard')
    else:
        form = EmployerInterestForm()

    return render(request, 'challenges/express_interest.html', {
        'form': form,
        'student': student,
    })


# ─── Sponsor Challenges ───────────────────────────────────────────────────────


@login_required
def sponsor_challenge_view(request):
    if request.user.user_type != 'employer':
        messages.error(request, 'Only employers can sponsor challenges.')
        return redirect('dashboard:home')

    if request.method == 'POST':
        company = request.user.employer_profile.company_name

        inquiry = SponsorshipInquiry.objects.create(
            employer=request.user,
            discipline_interest=request.POST.get('challenge_interest', '')[:100],
            budget=request.POST.get('budget', '')[:100],
            message=request.POST.get('message', ''),
        )

        super_admins = User.objects.filter(user_type='super_admin')
        for sa in super_admins:
            Notification.objects.create(
                recipient=sa,
                message=f'{company} wants to sponsor a challenge '
                        f'({inquiry.discipline_interest or "any discipline"}).',
                notification_type='general',
                link='/management/sponsorships/',
            )

        safe_send_mail(
            subject='ConnectED — Sponsorship Interest',
            message=(
                f'{company} is interested in sponsoring a challenge.\n\n'
                f'Contact: {request.user.employer_profile.company_email}\n'
                f'Discipline: {inquiry.discipline_interest or "Open"}\n'
                f'Budget: {inquiry.budget or "Not stated"}\n\n'
                f'Message:\n{inquiry.message}\n\n'
                f'Manage it: {django_settings.SITE_URL}/management/sponsorships/'
            ),
            recipient_list=[sa.email for sa in super_admins],
        )

        messages.success(
            request,
            'Your sponsorship interest has been sent. '
            'Our team will contact you within 2 business days.'
        )
        return redirect('challenges:sponsor')

    challenges = Challenge.objects.filter(is_active=True)
    return render(request, 'challenges/sponsor_challenges.html', {'challenges': challenges})