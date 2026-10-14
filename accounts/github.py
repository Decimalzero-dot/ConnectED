import re
import logging
import requests
from django import forms
from django.conf import settings

logger = logging.getLogger(__name__)

API = 'https://api.github.com'
TIMEOUT = 5  # seconds per call; keeps the worst case under gunicorn's 30s limit

REPO_RE = re.compile(
    r'^https?://(?:www\.)?github\.com/'
    r'(?P<owner>[A-Za-z0-9-]{1,39})/'
    r'(?P<repo>[A-Za-z0-9._-]+?)'
    r'(?:\.git)?(?:[/?#].*)?$',
    re.IGNORECASE,
)
USERNAME_RE = re.compile(r'^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$')


def _get(path, **params):
    headers = {
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
    }
    if settings.GITHUB_API_TOKEN:
        headers['Authorization'] = f'Bearer {settings.GITHUB_API_TOKEN}'
    return requests.get(f'{API}{path}', headers=headers,
                        params=params or None, timeout=TIMEOUT)


def normalize_username(value):
    """Accepts 'alice', '@alice' or 'https://github.com/alice'."""
    v = (value or '').strip()
    v = re.sub(r'^https?://(?:www\.)?github\.com/', '', v, flags=re.IGNORECASE)
    return v.lstrip('@').split('/')[0]


def check_username(name):
    """Returns ('ok', canonical_login) | ('fail', message) | ('unavailable', name)."""
    if not USERNAME_RE.match(name):
        return 'fail', 'That is not a valid GitHub username.'
    try:
        r = _get(f'/users/{name}')
    except requests.RequestException:
        return 'unavailable', name
    if r.status_code == 404:
        return 'fail', f'No GitHub account named "{name}" exists. Check the spelling.'
    if r.status_code != 200:
        return 'unavailable', name
    data = r.json()
    if data.get('type') != 'User':
        return 'fail', f'"{name}" is an organisation, not a personal account.'
    return 'ok', data['login']


def verify_repo(url, username):
    """
    Returns (status, message, canonical_url)
      'ok'          -> message is a reviewer-facing summary
      'fail'        -> message is shown to the student; submission is blocked
      'unavailable' -> GitHub could not be reached; submission is allowed but flagged
    """
    m = REPO_RE.match((url or '').strip())
    if not m:
        return 'fail', ('That does not look like a GitHub repository link. '
                        'Use the format https://github.com/username/repo-name'), url

    owner, repo = m.group('owner'), m.group('repo')
    unavailable = 'GitHub could not verify this repository right now.'

    try:
        r = _get(f'/repos/{owner}/{repo}')
        if r.status_code == 404:
            return 'fail', (f'We could not find {owner}/{repo} on GitHub. '
                            'Check the link and make sure the repository is public.'), url
        if r.status_code != 200:
            logger.warning('GitHub API returned %s for %s/%s', r.status_code, owner, repo)
            return 'unavailable', unavailable, url

        data = r.json()
        real_owner, name = data['owner']['login'], data['name']
        canonical = f'https://github.com/{real_owner}/{name}'

        # Check whether the repository contains commits
        c = _get(
            f'/repos/{real_owner}/{name}/commits',
            per_page=1
        )

        if c.status_code == 409:
            return (
                'fail',
                'This repository is empty. Push your code to it, then submit again.',
                canonical
            )

        if c.status_code != 200:
            logger.warning(
                'GitHub commits API returned %s for %s/%s',
                c.status_code, real_owner, name
            )
            return 'unavailable', unavailable, canonical

        commits = c.json()

        # Handle a successful response with no commits
        if not commits:
            return (
                'fail',
                'This repository has no commits. Push your code before submitting.',
                canonical
            )

        last_commit = commits[0]['commit']['committer']['date'][:10]


        # Does the repo belong to this student?
        if real_owner.lower() == username.lower():
            relation = f'owned by @{real_owner}'
        else:
            k = _get(f'/repos/{real_owner}/{name}/contributors', per_page=100)
            if k.status_code != 200:
                return 'unavailable', unavailable, canonical
            logins = {u.get('login', '').lower() for u in k.json()}
            if username.lower() not in logins:
                return 'fail', (
                    f'This repository belongs to @{real_owner}, and @{username} is not '
                    f'listed as a contributor. Submit a repository you created or '
                    f'contributed to. For team projects, make sure your commits are '
                    f'linked to your GitHub account.'), canonical
            relation = f'@{username} is a contributor (owner: @{real_owner})'

    except (requests.RequestException, KeyError, ValueError, IndexError):
        logger.exception('GitHub verification error for %s/%s', owner, repo)
        return 'unavailable', unavailable, url

    summary = f'Public repo; {relation}; last commit {last_commit}'
    if data.get('fork'):
        parent = (data.get('parent') or {}).get('full_name', 'another repository')
        summary += f'; FORK of {parent}'
    return 'ok', summary[:255], canonical


class GitHubUsernameFormMixin:
    """Checks a typed username exists, and locks it once verified via GitHub sign-in."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields.get('github_username')
        if field and getattr(self.instance, 'github_verified', False):
            field.disabled = True
            field.help_text = 'Verified through GitHub sign-in.'

    def clean_github_username(self):
        raw = self.cleaned_data.get('github_username', '')
        if not raw or 'github_username' not in self.changed_data:
            return raw
        status, result = check_username(normalize_username(raw))
        if status == 'fail':
            raise forms.ValidationError(result)
        return result  # canonical casing, or the typed name if GitHub was unreachable