import logging
from django.core.mail import send_mail, send_mass_mail
from django.conf import settings
import threading

logger = logging.getLogger(__name__)


MAX_RECIPIENTS = 10   # one event should never email more people than this


def safe_send_mail(subject, message, recipient_list):
    recipients = sorted({r.strip().lower() for r in recipient_list if r})
    if not recipients:
        return False
    if len(recipients) > MAX_RECIPIENTS:
        logger.error('Refused to email %d people for "%s"', len(recipients), subject)
        return False
    ok = True
    for r in recipients:   # one email each, so nobody sees anyone else's address
        try:
            send_mail(subject=subject, message=message,
                      from_email=settings.DEFAULT_FROM_EMAIL,
                      recipient_list=[r], fail_silently=False)
        except Exception:
            logger.exception('Email failed: %s', subject)
            ok = False
    return ok

def safe_send_mass_mail(datatuple):
    """Send many emails over one connection. Never raises, always logs."""
    if not datatuple:
        return False
    try:
        send_mass_mail(datatuple, fail_silently=False)
        return True
    except Exception:
        logger.exception("Mass email failed (%d messages)", len(datatuple))
        return False


def send_in_background(fn, *args, **kwargs):
    """Run a slow function (SMTP) off the request thread."""
    threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True).start()