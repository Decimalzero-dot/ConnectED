from django import forms
from accounts.models import Profile
from universities.models import University


class OnboardingForm(forms.ModelForm):
    university = forms.ModelChoiceField(
        queryset=University.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select your university"
    )

    class Meta:
        model = Profile
        fields = ('year_of_study', 'discipline', 'github_username', 'reg_number')
        widgets = {
            'year_of_study': forms.Select(attrs={'class': 'form-control'}),
            'discipline': forms.Select(attrs={'class': 'form-control'}),
            'github_username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'your-github-username'}),
            'reg_number': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. SCT211-0050/2022'}),
        }
   