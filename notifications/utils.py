import logging
from django.core.mail import send_mail, send_mass_mail
from django.conf import settings
import threading

logger = logging.getLogger(__name__)


def safe_send_mail(subject, message, recipient_list):
    """
    Send an email without ever raising. A failed email must never
    break the action that triggered it (submit, review, etc).
    """
    recipient_list = [r for r in recipient_list if r]
    if not recipient_list:
        return False
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False,
        )
        return True
    except Exception:
        logger.exception("Email failed: %s", subject)
        return False

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