from django.db import models

# Create your models here.
from django.conf import settings
import uuid
import os


def submission_file_path(instance, filename):
    """Randomize stored filename to prevent enumeration attacks."""
    ext = os.path.splitext(filename)[1].lower()
    random_name = f"{uuid.uuid4().hex}{ext}"
    return f"submissions/{instance.submission.student.id}/{random_name}"


class Challenge(models.Model):
    DISCIPLINE_CHOICES = (
        ('software_eng', 'Software Engineering'),
        ('cybersecurity', 'Cybersecurity'),
        ('data_science', 'Data Science'),
        ('ui_ux', 'UI/UX Design'),
        ('networking', 'Networking'),
        ('ai_ml', 'AI / Machine Learning'),
    )
    DIFFICULTY_CHOICES = (
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('capstone', 'Capstone'),
    )
    SUBMISSION_TYPE_CHOICES = (
        ('github', 'GitHub Repository'),
        ('file_upload', 'File Upload'),
        ('external_url', 'External URL (Figma, Wokwi, etc.)'),
        ('text', 'Written Answer'),
    )

    title = models.CharField(max_length=200)
    description = models.TextField()
    objective = models.TextField(blank=True)
    requirements = models.TextField(blank=True)
    submission_instructions = models.TextField(blank=True)
    expected_skills = models.TextField(blank=True)
    discipline = models.CharField(max_length=20, choices=DISCIPLINE_CHOICES)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    track = models.CharField(
        max_length=10,
        choices=(('software', 'Software'), ('hardware', 'Hardware / IoT')),
        default='software'
    )
    min_year = models.PositiveSmallIntegerField(
        choices=((1,'1st Year'),(2,'2nd Year'),(3,'3rd Year'),(4,'4th Year')),
        default=1
    )
    points = models.PositiveIntegerField(default=10)
    deadline = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_challenges'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    # Which submission types are allowed for this challenge
    allows_github = models.BooleanField(default=True)
    allows_file_upload = models.BooleanField(default=False)
    allows_external_url = models.BooleanField(default=False)
    allows_text = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_difficulty_display()})"

    def is_eligible_for(self, profile):
        if not profile.discipline or not profile.year_of_study:
            return False
        return (
            profile.discipline == self.discipline and
            profile.year_of_study >= self.min_year
        )

    def allowed_submission_types(self):
        types = []
        if self.allows_github:
            types.append('github')
        if self.allows_file_upload:
            types.append('file_upload')
        if self.allows_external_url:
            types.append('external_url')
        if self.allows_text:
            types.append('text')
        return types


class Submission(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
    )

    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name='submissions'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submissions'
    )

    # Submission content — all optional, filled based on challenge type
    github_url = models.URLField(
        blank=True,
        help_text="GitHub repository URL"
    )
    external_url = models.URLField(
        blank=True,
        help_text="Figma, Wokwi, Tinkercad, YouTube, or other external link"
    )
    text_answer = models.TextField(
        blank=True,
        help_text="Written answer or explanation"
    )

    # Review fields
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    score = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Score out of challenge points"
    )
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.username} → {self.challenge.title} ({self.status})"

    def has_content(self):
        """Check if at least one submission method was filled."""
        return bool(
            self.github_url or
            self.external_url or
            self.text_answer or
            self.files.exists()
        )


class SubmissionFile(models.Model):
    ALLOWED_EXTENSIONS = [
        '.pdf', '.docx', '.png', '.jpg', '.jpeg',
        '.ipynb', '.csv', '.pkt', '.zip'
    ]

    submission = models.ForeignKey(
        Submission,
        on_delete=models.CASCADE,
        related_name='files'
    )
    file = models.FileField(upload_to=submission_file_path)
    original_filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(help_text="Size in bytes")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.original_filename} ({self.submission})"

    def extension(self):
        return os.path.splitext(self.original_filename)[1].lower()


    
class EmployerInterest(models.Model):
    JOB_TYPE_CHOICES = (
        ('internship', 'Internship'),
        ('attachment', 'Industrial Attachment'),
        ('part_time', 'Part Time'),
        ('full_time', 'Full Time'),
        ('contract', 'Contract'),
    )

    employer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='interests_sent'
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='interests_received'
    )
    job_type = models.CharField(max_length=20, choices=JOB_TYPE_CHOICES)
    message = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=(
            ('pending', 'Pending'),
            ('forwarded', 'Forwarded to Student'),
            ('closed', 'Closed'),
        ),
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['employer', 'student']

    def __str__(self):
        return f"{self.employer.employer_profile.company_name} → {self.student.username}"