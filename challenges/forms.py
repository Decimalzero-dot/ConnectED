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
           'title', 'description', 'objective', 'requirements',
            'submission_instructions', 'expected_skills',
            'discipline', 'difficulty', 'min_year',
            'points', 'deadline', 'is_active'
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
            'objective': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'requirements': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'One requirement per line'
            }),
            'submission_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'expected_skills': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Python, conditionals, functions'
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