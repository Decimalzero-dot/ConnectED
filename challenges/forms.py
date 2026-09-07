from django import forms
from .models import Submission, Challenge, EmployerInterest


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ('github_repo_url',)

        widgets = {
            'github_repo_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://github.com/your-username/your-repo'
            }),
        }


class ChallengeForm(forms.ModelForm):
    class Meta:
        model = Challenge
        fields = (
            'title',
            'description',
            'discipline',
            'difficulty',
            'min_year',
            'points',
            'deadline',
            'is_active'
        )

        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4
            }),
            'discipline': forms.Select(attrs={'class': 'form-control'}),
            'difficulty': forms.Select(attrs={'class': 'form-control'}),
            'min_year': forms.Select(attrs={'class': 'form-control'}),
            'points': forms.NumberInput(attrs={'class': 'form-control'}),
            'deadline': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
        }


class EmployerInterestForm(forms.ModelForm):
    class Meta:
        model = EmployerInterest
        fields = ('job_type', 'message')

        widgets = {
            'job_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': (
                    'Introduce your company and explain why you are '
                    'interested in this student...'
                )
            }),
        }