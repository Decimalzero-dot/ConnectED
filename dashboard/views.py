from django.shortcuts import render, redirect

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import OnboardingForm
from django.db.models import Sum, Count, Q
from challenges.models import Submission
from accounts.models import Profile


@login_required
def onboarding_view(request):
    profile = request.user.profile

    if profile.onboarding_complete:
        return redirect('dashboard:home')

    if request.method == 'POST':
        form = OnboardingForm(request.POST, instance=profile)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.onboarding_complete = True
            profile.save()
            messages.success(request, 'Welcome to ConnectED!')
            return redirect('dashboard:home')
    else:
        form = OnboardingForm(instance=profile)

    return render(request, 'dashboard/onboarding.html', {'form': form})


@login_required
def home_view(request):
    profile = request.user.profile

    if not profile.onboarding_complete:
        return redirect('dashboard:onboarding')

    context = {
        'profile': profile,
        'university': profile.university,
        'year_of_study': profile.get_year_of_study_display(),
        'discipline': profile.get_discipline_display(),
    }

    # Year-based access logic
    if profile.year_of_study == 1:
        context['access_level'] = 'beginner'
        context['message'] = 'Welcome! Start with beginner challenges to build your foundation.'
    elif profile.year_of_study == 2:
        context['access_level'] = 'intermediate'
        context['message'] = 'You can now join cross-campus teams and intermediate challenges.'
    elif profile.year_of_study == 3:
        context['access_level'] = 'advanced'
        context['message'] = 'Advanced challenges and mentorship opportunities are open to you.'
    else:
        context['access_level'] = 'capstone'
        context['message'] = 'Capstone projects and recruiter-visible profiles are now active.'

    return render(request, 'dashboard/home.html', context)


@login_required
def leaderboard_view(request):
    profile = request.user.profile

    # Base: only passed submissions count toward score
    passed_submissions = Submission.objects.filter(status='passed')

    # Filters from query params
    scope = request.GET.get('scope', 'campus')   # campus | discipline | year | global
    discipline_filter = request.GET.get('discipline', profile.discipline)
    year_filter = request.GET.get('year', profile.year_of_study)

    # Always start from passed submissions, join to student profile
    queryset = passed_submissions.select_related('student__profile', 'challenge')

    if scope == 'campus':
        queryset = queryset.filter(student__profile__university=profile.university)
    elif scope == 'discipline':
        queryset = queryset.filter(
            student__profile__university=profile.university,
            student__profile__discipline=discipline_filter
        )
    elif scope == 'year':
        queryset = queryset.filter(
            student__profile__university=profile.university,
            student__profile__year_of_study=year_filter
        )
    # scope == 'global' → no filter, everyone counts

    # Aggregate: total points + challenge count per student
    leaderboard = (
        queryset
        .values('student__id', 'student__username', 'student__profile__university__name')
        .annotate(total_points=Sum('challenge__points'), challenges_completed=Count('id'))
        .order_by('-total_points')
    )

    context = {
        'leaderboard': leaderboard,
        'scope': scope,
        'discipline_filter': discipline_filter,
        'year_filter': year_filter,
        'discipline_choices': Profile.DISCIPLINE_CHOICES,
        'year_choices': Profile.YEAR_CHOICES,
        'user_university': profile.university,
    }
    return render(request, 'dashboard/leaderboard.html', context)