from django import forms
from .models import Submission


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