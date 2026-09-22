from django import forms
from .models import Challenge, Submission, SubmissionFile, EmployerInterest
from .utils import validate_submission_file


class ChallengeForm(forms.ModelForm):
    class Meta:
        model = Challenge
        fields = (
            'title', 'description', 'objective', 'requirements',
            'submission_instructions', 'expected_skills',
            'discipline', 'track', 'difficulty', 'min_year', 'points',
            'deadline', 'is_active',
            'allows_github', 'allows_file_upload',
            'allows_external_url', 'allows_text'
        )
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'objective': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'requirements': forms.Textarea(attrs={
                'class': 'form-control', 'rows': 4,
                'placeholder': 'One requirement per line'
            }),
            'submission_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'expected_skills': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. Python, conditionals, functions'
            }),
            'discipline': forms.Select(attrs={'class': 'form-control'}),
            'track': forms.Select(attrs={'class': 'form-control'}),
            'difficulty': forms.Select(attrs={'class': 'form-control'}),
            'min_year': forms.Select(attrs={'class': 'form-control'}),
            'points': forms.NumberInput(attrs={'class': 'form-control'}),
            'deadline': forms.DateTimeInput(attrs={
                'class': 'form-control', 'type': 'datetime-local'
            }),
        }

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True
class SubmissionForm(forms.ModelForm):
    """
    Generic submission form — fields shown/hidden based on
    what the challenge allows. Validated in the view.
    """
    uploaded_files = forms.FileField(
    required=False,
        widget=MultipleFileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.docx,.png,.jpg,.jpeg,.ipynb,.csv,.pkt,.zip'
        }),
        help_text="Allowed: PDF, DOCX, PNG, JPG, IPYNB, CSV, PKT, ZIP (max 10MB each)"
    )

    class Meta:
        model = Submission
        fields = ('github_url', 'external_url', 'text_answer')
        widgets = {
            'github_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://github.com/username/repo'
            }),
            'external_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'Figma, Wokwi, Tinkercad, YouTube, or other link'
            }),
            'text_answer': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 6,
                'placeholder': 'Write your answer here...'
            }),
        }


class EmployerInterestForm(forms.ModelForm):
    class Meta:
        model = EmployerInterest
        fields = ('job_type', 'message')
        widgets = {
            'job_type': forms.Select(attrs={'class': 'form-control'}),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Introduce your company and explain why you are interested in this student...'
            }),
        }

