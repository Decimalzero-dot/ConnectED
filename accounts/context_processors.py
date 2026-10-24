def user_preferences(request):
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            return {
                'dark_mode': profile.dark_mode,
                'font_size': profile.font_size,
            }
        except Exception:
            pass
    return {
        'dark_mode': False,
        'font_size': 'medium',
    }
TOUR_VERSION = 1   

def tour_state(request):
    u = getattr(request, 'user', None)
    if not (u and u.is_authenticated):
        return {}
    show = u.tour_version_seen < TOUR_VERSION
    if show and u.user_type == 'student':   # not during onboarding
        profile = getattr(u, 'profile', None)
        show = bool(profile and profile.onboarding_complete)
    return {'show_tour': show}