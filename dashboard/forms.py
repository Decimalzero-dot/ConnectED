from django import forms
from accounts.models import Profile
from universities.models import University
from accounts.github import GitHubUsernameFormMixin

class OnboardingForm(GitHubUsernameFormMixin, forms.ModelForm):
    university = forms.ModelChoiceField(
        queryset=University.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="Select your university"
    )
    first_name = forms.CharField(max_length=150, widget=forms.TextInput(
        attrs={'class': 'form-control', 'autocomplete': 'given-name'}))
    last_name = forms.CharField(max_length=150, widget=forms.TextInput(
        attrs={'class': 'form-control', 'autocomplete': 'family-name'}))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['year_of_study'].required = True
        if user is not None:   # Google sign-in already filled these
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
        self.order_fields(['first_name', 'last_name', 'year_of_study',
                           'github_username', 'reg_number', 'personal_email'])

    class Meta:
        model = Profile
        fields = ('year_of_study', 'github_username', 'reg_number', 'personal_email')
        widgets = {
            'year_of_study': forms.Select(attrs={'class': 'form-control'}),
            'github_username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'your-github-username'}),
            'reg_number': forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g. COM/M/0050/2022'}),
            'personal_email': forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Personal email for notifications'
            }),
        }
        
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.fields['year_of_study'].required = True
    
