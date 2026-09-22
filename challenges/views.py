from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from django.http import FileResponse, Http404
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from .models import Challenge, Submission, SubmissionFile, EmployerInterest
from .forms import SubmissionForm, ChallengeForm, EmployerInterestForm
from .utils import validate_submission_file
from notifications.models import Notification
from django.core.mail import send_mail
from django.conf import settings as django_settings

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
    # Employers see sponsor page, not student challenge list
    if request.user.user_type == 'employer':
        return redirect('challenges:sponsor')

    challenges = Challenge.objects.filter(is_active=True)
    profile = request.user.profile

    discipline_filter = request.GET.get('discipline')
    if discipline_filter:
        challenges = challenges.filter(discipline=discipline_filter)

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
    })


# ─── Challenge Detail + Submission ────────────────────────────────────────────

@login_required
def challenge_detail(request, pk):
    challenge = get_object_or_404(Challenge, pk=pk, is_active=True)
    profile = request.user.profile
    eligible = challenge.is_eligible_for(profile)

    existing_submission = Submission.objects.filter(
        challenge=challenge,
        student=request.user
    ).prefetch_related('files').first()

    form = None
    file_errors = []

    if eligible and not existing_submission and request.method == 'POST':
        form = SubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.challenge = challenge
            submission.student = request.user

            files = request.FILES.getlist('uploaded_files')

            # At least one submission method required
            if not any([
                submission.github_url,
                submission.external_url,
                submission.text_answer,
                files
            ]):
                form.add_error(None, 'Please provide at least one submission method.')
            else:
                # Validate files before saving anything
                validated_files = []
                for f in files:
                    try:
                        validate_submission_file(f)
                        validated_files.append(f)
                    except ValidationError as e:
                        file_errors.extend(e.messages)

                if not file_errors:
                    submission.save()

                    for f in validated_files:
                        SubmissionFile.objects.create(
                            submission=submission,
                            file=f,
                            original_filename=f.name,
                            file_size=f.size
                        )

                    # Notify campus admins
                    campus_admins = User.objects.filter(
                        user_type='campus_admin',
                        profile__university=request.user.profile.university
                    )
                    for admin in campus_admins:
                        Notification.objects.create(
                            recipient=admin,
                            message=(
                                f'{request.user.username} submitted '
                                f'"{challenge.title}" — awaiting review.'
                            ),
                            notification_type='general',
                            link=f'/challenges/review/{submission.pk}/'
                        )

                    admin_emails = [a.email for a in campus_admins if a.email]
                    if admin_emails:
                        send_mail(
                            subject=f'ConnectED — New Submission: {challenge.title}',
                            message=(
                                f'A student has submitted a solution for "{challenge.title}".\n\n'
                                f'Student: {request.user.username}\n'
                                f'University: {request.user.profile.university}\n\n'
                                f'Review it at: /challenges/review/{submission.pk}/'
                            ),
                            from_email=django_settings.DEFAULT_FROM_EMAIL,
                            recipient_list=admin_emails,
                            fail_silently=True,
                        )

                    messages.success(request, 'Submission received! Awaiting review.')
                    return redirect('challenges:detail', pk=challenge.pk)

    elif eligible and not existing_submission:
        form = SubmissionForm()

    return render(request, 'challenges/challenge_detail.html', {
        'challenge': challenge,
        'eligible': eligible,
        'submission': existing_submission,
        'form': form,
        'file_errors': file_errors,
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
    submission = get_object_or_404(Submission, pk=pk)

    if request.user.user_type == 'campus_admin':
        if submission.student.profile.university != request.user.profile.university:
            messages.error(request, 'You can only review submissions from your campus.')
            return redirect('challenges:review_queue')

    if request.method == 'POST':
        decision = request.POST.get('decision')
        feedback = request.POST.get('feedback', '')
        score = request.POST.get('score')

        if decision in ('passed', 'failed'):
            submission.status = decision
            submission.feedback = feedback
            submission.reviewed_at = timezone.now()
            if score:
                try:
                    submission.score = int(score)
                except ValueError:
                    pass
            submission.save()

            # In-platform notification
            Notification.objects.create(
                recipient=submission.student,
                message=(
                    f'Your submission for "{submission.challenge.title}" '
                    f'was marked {decision}.'
                    + (
                        f' Score: {submission.score}/{submission.challenge.points}'
                        if submission.score else ''
                    )
                ),
                notification_type='submission_reviewed',
                link=f'/challenges/{submission.challenge.pk}/'
            )

            # Email notification
            if submission.student.profile.notify_on_review:
                recipient_email = (
                    submission.student.profile.personal_email or
                    submission.student.email
                )
                if recipient_email:
                    send_mail(
                        subject=(
                            f'ConnectED — Submission {decision.title()}: '
                            f'{submission.challenge.title}'
                        ),
                        message=(
                            f'Hi {submission.student.username},\n\n'
                            f'Your submission for "{submission.challenge.title}" '
                            f'has been marked {decision.upper()}.\n\n'
                            + (
                                f'Score: {submission.score}/{submission.challenge.points} points\n\n'
                                if submission.score else ''
                            )
                            + (
                                f'Feedback:\n{feedback}\n\n'
                                if feedback else ''
                            )
                            + f'View your submission: /challenges/{submission.challenge.pk}/\n\n'
                            f'Keep building — The ConnectED Team'
                        ),
                        from_email=django_settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[recipient_email],
                        fail_silently=True,
                    )

            messages.success(request, f'Submission marked as {decision}.')
            return redirect('challenges:review_queue')

    return render(request, 'challenges/review_submission.html', {
        'submission': submission,
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
                send_mail(
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
                    from_email=django_settings.DEFAULT_FROM_EMAIL,
                    recipient_list=admin_emails,
                    fail_silently=True,
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
        challenge_interest = request.POST.get('challenge_interest', '')
        budget = request.POST.get('budget', '')
        message = request.POST.get('message', '')

        super_admins = User.objects.filter(user_type='super_admin')

        for sa in super_admins:
            Notification.objects.create(
                recipient=sa,
                message=(
                    f'{request.user.employer_profile.company_name} '
                    f'expressed interest in sponsoring a challenge.'
                ),
                notification_type='general',
                link='/management/employers/'
            )

        super_admin_emails = [sa.email for sa in super_admins if sa.email]
        if super_admin_emails:
            send_mail(
                subject='ConnectED — Sponsorship Interest',
                message=(
                    f'An employer is interested in sponsoring a challenge.\n\n'
                    f'Company: {request.user.employer_profile.company_name}\n'
                    f'Contact: {request.user.employer_profile.company_email}\n'
                    f'Challenge interest: {challenge_interest}\n'
                    f'Budget: {budget}\n\n'
                    f'Message:\n{message}'
                ),
                from_email=django_settings.DEFAULT_FROM_EMAIL,
                recipient_list=super_admin_emails,
                fail_silently=True,
            )

        messages.success(
            request,
            'Your sponsorship interest has been sent. '
            'Our team will contact you within 2 business days.'
        )
        return redirect('challenges:sponsor')

    challenges = Challenge.objects.filter(is_active=True)
    return render(request, 'challenges/sponsor_challenges.html', {
        'challenges': challenges,
    })