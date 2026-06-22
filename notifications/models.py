from django.db import models

# Create your models here.
from django.conf import settings


class Notification(models.Model):
    TYPE_CHOICES = (
        ('submission_reviewed', 'Submission Reviewed'),
        ('new_challenge', 'New Challenge'),
        ('general', 'General'),
    )

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    notification_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='general')
    link = models.CharField(max_length=255, blank=True)  # where clicking it takes you
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.recipient.username}: {self.message[:30]}"