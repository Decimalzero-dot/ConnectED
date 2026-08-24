from django import forms
from .models import User, Profile


class AccountSettingsForm(forms.ModelForm):
    """Username, email, profile photo"""
    class Meta:
        model = User
        fields = ('username', 'email', 'profile_image')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'profile_image': forms.FileInput(attrs={'class': 'form-control'}),
        }


class AcademicSettingsForm(forms.ModelForm):
    """Year, discipline, github, reg number"""
    class Meta:
        model = Profile
        fields = ('year_of_study', 'discipline', 'github_username', 'reg_number')
        widgets = {
            'year_of_study': forms.Select(attrs={'class': 'form-control'}),
            'discipline': forms.Select(attrs={'class': 'form-control'}),
            'github_username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'your-github-username'
            }),
            'reg_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. COM/M/0050/2022'
            }),
        }


class AppearanceSettingsForm(forms.ModelForm):
    """Dark mode, font size"""
    class Meta:
        model = Profile
        fields = ('dark_mode', 'font_size')
        widgets = {
            'dark_mode': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'font_size': forms.Select(attrs={'class': 'form-control'}),
        }


class NotificationSettingsForm(forms.ModelForm):
    """Email notification toggles"""
    class Meta:
        model = Profile
        fields = ('notify_on_review', 'notify_on_new_challenge')
        widgets = {
            'notify_on_review': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_on_new_challenge': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class PasswordChangeSettingsForm(forms.Form):
    """Change password while logged in"""
    current_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Current password'})
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New password'}),
        min_length=8
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm new password'})
    )

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_password = cleaned_data.get('confirm_password')
        if new_password and confirm_password and new_password != confirm_password:
            raise forms.ValidationError('New passwords do not match.')
        return cleaned_data