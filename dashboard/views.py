from django.shortcuts import render, redirect

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import OnboardingForm


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