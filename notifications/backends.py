import logging
import time
import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)
API_URL = 'https://api.resend.com/emails'


class ResendEmailBackend(BaseEmailBackend):
    """Sends Django emails over HTTPS through Resend. Railway's smaller plans block SMTP."""

    def _post(self, payload):
        for attempt in (1, 2):
            r = requests.post(API_URL, json=payload, timeout=10,
                              headers={'Authorization': f'Bearer {settings.RESEND_API_KEY}'})
            if r.status_code == 429 and attempt == 1:     # Resend allows about 2 requests a second
                time.sleep(1)
                continue
            if r.status_code >= 400:
                raise RuntimeError(f'Resend {r.status_code}: {r.text[:300]}')
            return

    def send_messages(self, email_messages):
        sent = 0
        for m in email_messages:
            payload = {'from': m.from_email or settings.DEFAULT_FROM_EMAIL,
                       'to': list(m.to), 'subject': m.subject, 'text': m.body}
            if m.cc:
                payload['cc'] = list(m.cc)
            if m.bcc:
                payload['bcc'] = list(m.bcc)
            for body, mimetype in getattr(m, 'alternatives', []):
                if mimetype == 'text/html':
                    payload['html'] = body
            try:
                self._post(payload)
                sent += 1
            except Exception:
                logger.exception('Resend failed: %s', m.subject)
                if not self.fail_silently:
                    raise
        return sent