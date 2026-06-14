from django.contrib import admin

# Register your models here.
from .models import Challenge, Submission


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ('title', 'discipline', 'difficulty', 'min_year', 'points', 'is_active', 'created_at')
    list_filter = ('discipline', 'difficulty', 'min_year', 'is_active')
    search_fields = ('title', 'description')


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ('student', 'challenge', 'status', 'submitted_at', 'reviewed_at')
    list_filter = ('status', 'challenge__discipline')
    search_fields = ('student__username', 'challenge__title')
    readonly_fields = ('submitted_at',)