from django.db import models

# Create your models here.
from django.conf import settings


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

    title = models.CharField(max_length=200)
    description = models.TextField()
    discipline = models.CharField(max_length=20, choices=DISCIPLINE_CHOICES)
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    min_year = models.PositiveSmallIntegerField(
        choices=((1, '1st Year'), (2, '2nd Year'), (3, '3rd Year'), (4, '4th Year')),
        default=1,
        help_text="Minimum year of study required to attempt this challenge"
    )
    points = models.PositiveIntegerField(default=10)
    deadline = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_challenges')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_difficulty_display()})"

    def is_eligible_for(self, profile):
        """Check if a student's profile meets discipline + year requirements."""
        if not profile.discipline or not profile.year_of_study:
            return False
        return profile.discipline == self.discipline and profile.year_of_study >= self.min_year


class Submission(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
    )

    challenge = models.ForeignKey(Challenge, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='submissions')
    github_repo_url = models.URLField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"{self.student.username} → {self.challenge.title} ({self.status})"