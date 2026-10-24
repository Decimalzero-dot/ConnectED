from django.shortcuts import render, redirect
from django_ratelimit.exceptions import Ratelimited
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from challenges.models import Challenge
from universities.models import University
from django.urls import NoReverseMatch, reverse


def _open_challenges():
    """Active challenges whose deadline hasn't passed: safe to show publicly."""
    return Challenge.objects.filter(is_active=True).filter(
        Q(deadline__isnull=True) | Q(deadline__gt=timezone.now()))

def _google_ready():
    """Show the Google button only when it can actually work."""
    if not getattr(settings, 'GOOGLE_CLIENT_ID', ''):
        return False
    try:
        reverse('accounts:google_login')
    except NoReverseMatch:
        return False
    return True


def _signed_in_redirect(request, pk=None):
    """Logged-in users don't need the public pages."""
    if request.user.user_type == 'employer':
        return redirect('challenges:sponsor')
    if pk is not None:
        return redirect('challenges:detail', pk=pk)
    return redirect('challenges:list')


def landing_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')

    open_qs = _open_challenges()

    # Beginner-friendly picks, Guided ones first. Sorting in Python means this
    # keeps working even before the `guided` field migration has been applied.
    pool = list(open_qs.filter(difficulty='beginner', min_year=1).order_by('points')[:12])
    starter = sorted(pool, key=lambda c: not getattr(c, 'guided', False))[:3]

    labels = dict(Challenge.DISCIPLINE_CHOICES)
    tracks = [
        {'key': r['discipline'], 'label': labels.get(r['discipline'], r['discipline']), 'count': r['n']}
        for r in open_qs.values('discipline').annotate(n=Count('id')).order_by('-n')
    ]
    User = get_user_model()
    return render(request, 'core/landing.html', {
        'starter': starter,
        'tracks': tracks,
        'stats': {
            'challenges': open_qs.count(),
            'fields': len(tracks),
            'universities': University.objects.filter(is_active=True).count(),
            'students': User.objects.filter(user_type='student').count(),
        },
        'google_enabled': _google_ready(),
    })

def explore_view(request):
    if request.user.is_authenticated:
        return _signed_in_redirect(request)

    field = request.GET.get('field', '')
    level = request.GET.get('level', '')

    if field not in dict(Challenge.DISCIPLINE_CHOICES):
        field = ''

    if level not in dict(Challenge.DIFFICULTY_CHOICES):
        level = ''

    qs = _open_challenges()

    if field:
        qs = qs.filter(discipline=field)

    if level:
        qs = qs.filter(difficulty=level)

    challenges = qs.order_by('min_year', '-guided', 'points')

    return render(request, 'core/explore.html', {
        'challenges': challenges,
        'fields': Challenge.DISCIPLINE_CHOICES,
        'levels': Challenge.DIFFICULTY_CHOICES,
        'field': field,
        'level': level,
    })

def explore_detail(request, pk):
    if request.user.is_authenticated:
        return _signed_in_redirect(request, pk)
    return render(request, 'core/explore_detail.html',
                  {'challenge': get_object_or_404(_open_challenges(), pk=pk)})

def landing_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home')
    return render(request, 'core/landing.html')


def error_404(request, exception):
    return render(request, 'errors/404.html', status=404)


def error_500(request):
    return render(request, 'errors/500.html', status=500)


def error_403(request, exception):
    return render(request, 'errors/403.html', status=403)

def privacy_view(request):
    return render(request, 'core/privacy.html')

def error_403(request, exception=None):
    if isinstance(exception, Ratelimited):
        return render(request, 'errors/429.html', status=429)
    return render(request, 'errors/403.html', status=403)