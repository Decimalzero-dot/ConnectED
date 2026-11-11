from django.conf import settings
from django.contrib.auth import get_user_model

from .models import Notification
from .utils import safe_send_mail


def _site(path):
    return f'{settings.SITE_URL}{path}'


def _emails(users):
    return [u.email for u in users if u.email]


def _super_admins():
    return list(get_user_model().objects.filter(user_type='super_admin'))


def employer_needs_verification(emp):
    """A new employer registered. Tell the super admins."""
    admins = _super_admins()
    Notification.objects.bulk_create([
        Notification(recipient=a, notification_type='general', link='/management/employers/',
                     message=f'New employer awaiting verification: {emp.company_name}.')
        for a in admins])
    safe_send_mail(
        subject=f'ConnectED — employer needs verification: {emp.company_name}',
        message=(f'{emp.company_name} has registered and cannot sign in until you verify them.\n\n'
                 f'Contact: {emp.company_email}\n'
                 f'Industry: {emp.industry or "not given"}\n'
                 f'Website: {emp.company_website or "not given"}\n\n'
                 f'Check them out, then verify or reject:\n{_site("/management/employers/")}'),
        recipient_list=_emails(admins))


def employer_decision(emp, verified):
    """A super admin verified or rejected an employer. Tell the employer."""
    if not settings.EMAIL_EMPLOYER_DECISION: return
    if verified:
        subject = 'Your ConnectED account is verified'
        body = (f'Hi {emp.company_name},\n\nYour employer account has been verified. '
                f'You can sign in and browse students now:\n{_site("/accounts/login/")}\n\n'
                f'The ConnectED Team')
    else:
        subject = 'Your ConnectED employer registration'
        body = (f'Hi {emp.company_name},\n\nWe could not verify your employer registration this time. '
                f'If you think this is a mistake, reply to this email and tell us about your '
                f'organisation.\n\nThe ConnectED Team')
    safe_send_mail(subject=subject, message=body, recipient_list=[emp.company_email])


def sponsorship_enquiry(inq):
    """An employer asked about sponsoring a challenge. Tell the super admins."""
    admins = _super_admins()
    emp = inq.employer.employer_profile
    Notification.objects.bulk_create([
        Notification(recipient=a, notification_type='general', link='/management/sponsorships/',
                     message=f'{emp.company_name} wants to sponsor a challenge '
                             f'({inq.discipline_interest or "any field"}).')
        for a in admins])
    safe_send_mail(
        subject=f'ConnectED — sponsorship enquiry from {emp.company_name}',
        message=(f'{emp.company_name} is interested in sponsoring a challenge.\n\n'
                 f'Contact: {emp.company_email}\n'
                 f'Field: {inq.discipline_interest or "open"}\n'
                 f'Budget: {inq.budget or "not stated"}\n\n'
                 f'Message:\n{inq.message or "(none)"}\n\n'
                 f'Manage it: {_site("/management/sponsorships/")}'),
        recipient_list=_emails(admins))


def employer_interest(interest):
    """An employer wants to reach a student. Tell that student's campus admins."""
    User = get_user_model()
    student, emp = interest.student, interest.employer.employer_profile
    admins = list(User.objects.filter(user_type='campus_admin',
                                      profile__university=student.profile.university))
    if not admins:          # no campus admin yet: don't let the request vanish
        admins = _super_admins()
    Notification.objects.bulk_create([
        Notification(recipient=a, notification_type='general', link='/management/employer-interests/',
                     message=f'{emp.company_name} is interested in {student.username} '
                             f'({interest.get_job_type_display()}).')
        for a in admins])
    safe_send_mail(
        subject=f'ConnectED — {emp.company_name} is interested in {student.username}',
        message=(f'{emp.company_name} would like to connect with {student.username}.\n\n'
                 f'Opportunity: {interest.get_job_type_display()}\n'
                 f'Employer contact: {emp.company_email}\n\n'
                 f'Their message:\n{interest.message}\n\n'
                 f'Review it and forward it if it looks genuine:\n{_site("/management/employer-interests/")}'),
        recipient_list=_emails(admins))


def interest_forwarded(interest):
    """A campus admin forwarded an employer's interest. Tell the student."""
    student, emp = interest.student, interest.employer.employer_profile
    Notification.objects.create(
        recipient=student, notification_type='general', link='/dashboard/opportunities/',
        message=f'{emp.company_name} is interested in you ({interest.get_job_type_display()}). Tap to view.')
    if not settings.EMAIL_INTEREST_FORWARDED: return
    to = student.profile.personal_email or student.email
    safe_send_mail(
        subject=f'{emp.company_name} is interested in your work',
        message=(f'Hi {student.first_name or student.username},\n\n'
                 f'{emp.company_name} has shown interest in you for a '
                 f'{interest.get_job_type_display()} opportunity, and your campus admin has passed it on.\n\n'
                 f'Their message:\n{interest.message}\n\n'
                 f'You can reach them at {emp.company_email}.\n'
                 f'Details: {_site("/dashboard/opportunities/")}\n\nThe ConnectED Team'),
        recipient_list=[to])