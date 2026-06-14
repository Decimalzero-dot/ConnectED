from django.shortcuts import render, get_object_or_404, redirect

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Challenge, Submission
from .forms import SubmissionForm


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

    # Get this student's latest submission for this challenge, if any
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