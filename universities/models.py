from django.db import models

# Create your models here.
from django.utils.text import slugify


class University(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    location = models.CharField(max_length=200, blank=True)
    logo = models.ImageField(upload_to='university_logos/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    email_domain = models.CharField(
        max_length=100,
        blank=True,
        help_text="Student email domain e.g. students.uok.ac.ke"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Universities"
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name