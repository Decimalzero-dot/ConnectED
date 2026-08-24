from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count
from .forms import OnboardingForm
from challenges.models import Submission, Challenge
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
def home_stats_api(request):
    """JSON API — returns current user's submission stats for the dashboard."""
    user = request.user

    submissions = Submission.objects.filter(student=user)

    total       = submissions.count()
    passed      = submissions.filter(status='passed').count()
    pending     = submissions.filter(status='pending').count()
    failed      = submissions.filter(status='failed').count()
    total_points = submissions.filter(status='passed').aggregate(
        pts=Sum('challenge__points')
    )['pts'] or 0

    # Last 5 submissions for the activity feed
    recent = submissions.select_related('challenge')[:5]
    recent_list = [
        {
            'challenge': s.challenge.title,
            'status': s.status,
            'points': s.challenge.points if s.status == 'passed' else 0,
            'submitted_at': s.submitted_at.strftime('%d %b %Y'),
        }
        for s in recent
    ]

    return JsonResponse({
        'total': total,
        'passed': passed,
        'pending': pending,
        'failed': failed,
        'total_points': total_points,
        'recent': recent_list,
    })


@login_required
def leaderboard_view(request):
    profile = request.user.profile

    passed_submissions = Submission.objects.filter(status='passed')

    scope             = request.GET.get('scope', 'campus')
    discipline_filter = request.GET.get('discipline') or profile.discipline or ''
    year_filter       = request.GET.get('year') or profile.year_of_study or 1

    queryset = passed_submissions.select_related(
        'student__profile', 'student__profile__university', 'challenge'
    )

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
    # scope == 'global' has no filter

    leaderboard = (
        queryset
        .values(
            'student__id',
            'student__username',
            'student__profile__university__name',
            'student__profile__discipline',
            'student__profile__year_of_study',
            'student__profile__github_username',
            'student__profile__reg_number',
        )
        .annotate(
            total_points=Sum('challenge__points'),
            challenges_completed=Count('id')
        )
        .order_by('-total_points')
    )

    # Calculate current user's 

    your_rank = None
    for i, entry in enumerate(leaderboard, start=1):
        if entry['student__username'] == request.user.username:
            your_rank = i
            break

    context = {
        'leaderboard': leaderboard,
        'scope': scope,
        'discipline_filter': discipline_filter,
        'year_filter': year_filter,
        'discipline_choices': Profile.DISCIPLINE_CHOICES,
        'year_choices': Profile.YEAR_CHOICES,
        'user_university': profile.university,
        'your_rank': your_rank,
        'scope_choices': [                        
                ('campus', 'My Campus'),
                ('discipline', 'By Discipline'),
                ('year', 'By Year'),
                ('global', 'Global'),
            ],
    }
    return render(request, 'dashboard/leaderboard.html', context)
