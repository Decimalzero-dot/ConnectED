from django.conf import settings
from django.http import HttpResponsePermanentRedirect


class CanonicalHostMiddleware:
    """301-redirect duplicate hostnames (www, the Railway address) to the main domain."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host().split(':')[0].lower()
        if host in settings.REDIRECT_HOSTS and request.method in ('GET', 'HEAD'):
            return HttpResponsePermanentRedirect(
                f'https://{settings.CANONICAL_HOST}{request.get_full_path()}')
        return self.get_response(request)