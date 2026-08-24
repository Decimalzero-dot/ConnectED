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