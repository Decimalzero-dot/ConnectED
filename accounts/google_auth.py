import base64
import json
import time
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.urls import reverse

AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
TOKEN_URL = 'https://oauth2.googleapis.com/token'


def redirect_uri():
    return f"{settings.SITE_URL}{reverse('accounts:google_callback')}"


def build_auth_url(state, nonce):
    return AUTH_URL + '?' + urlencode({
        'client_id': settings.GOOGLE_CLIENT_ID,
        'redirect_uri': redirect_uri(),
        'response_type': 'code',
        'scope': 'openid email profile',
        'state': state,
        'nonce': nonce,
        'prompt': 'select_account',
    })


def exchange_code(code):
    """Trade the one-time code for Google's ID token. Returns its claims or raises ValueError."""
    r = requests.post(TOKEN_URL, data={
        'code': code,
        'client_id': settings.GOOGLE_CLIENT_ID,
        'client_secret': settings.GOOGLE_CLIENT_SECRET,
        'redirect_uri': redirect_uri(),
        'grant_type': 'authorization_code',
    }, timeout=10)
    if r.status_code != 200:
        raise ValueError('token exchange failed')

    id_token = r.json().get('id_token')
    if not id_token:
        raise ValueError('no id_token')

    # The token came straight from Google over HTTPS, authenticated with our client
    # secret, so signature checks aren't needed (Google's docs say so). We still
    # validate the claims.
    payload = id_token.split('.')[1]
    payload += '=' * (-len(payload) % 4)
    claims = json.loads(base64.urlsafe_b64decode(payload))

    if claims.get('iss') not in ('https://accounts.google.com', 'accounts.google.com'):
        raise ValueError('bad issuer')
    if claims.get('aud') != settings.GOOGLE_CLIENT_ID:
        raise ValueError('bad audience')
    if claims.get('exp', 0) < time.time():
        raise ValueError('expired')
    if str(claims.get('email_verified')).lower() != 'true':
        raise ValueError('email not verified')
    if not claims.get('sub') or not claims.get('email'):
        raise ValueError('missing claims')
    return claims