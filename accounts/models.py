from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser
from universities.models import University
from django.db.models.signals import post_save
from django.dispatch import receiver


class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('student', 'Student'),
        ('campus_admin', 'Campus Admin'),
        ('super_admin', 'Super Admin'),
    )
    user_type = models.CharField(max_length=20, choices=USER_TYPE_CHOICES, default='student')
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)

    def __str__(self):
        return f"{self.username} - {self.email} - {self.user_type}"
    
    def is_student(self):
        return self.user_type == 'student'
    
    def is_campus_admin(self):
        return self.user_type == 'campus_admin'
    
    def is_super_admin(self):
        return self.user_type == 'super_admin'


class Profile(models.Model):
    YEAR_CHOICES = (
        (1, 'First Year'),
        (2, 'Second Year'),
        (3, 'Third Year'),
        (4, 'Fourth Year'),
    )
    DISCIPLINE_CHOICES = (
        ('software_eng', 'Software Engineering'),
        ('cybersecurity', 'Cybersecurity'),
        ('data_science', 'Data Science'),
        ('ui_ux', 'UI/UX Design'),
        ('networking', 'Networking'),
        ('ai_ml', 'AI / Machine Learning'),
    )

    user = models.OneToOneField('User', on_delete=models.CASCADE, related_name='profile')
    university = models.ForeignKey(University, on_delete=models.SET_NULL, null=True, blank=True, related_name='students')
    year_of_study = models.PositiveSmallIntegerField(choices=YEAR_CHOICES, null=True, blank=True)
    discipline = models.CharField(max_length=20, choices=DISCIPLINE_CHOICES, null=True, blank=True)
    github_username = models.CharField(max_length=100, blank=True)
    onboarding_complete = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s Profile"    
    
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)    