from django import forms
from .models import University


class UniversityForm(forms.ModelForm):
    class Meta:
        model = University
        fields = ('name', 'location', 'logo', 'is_active', 'email_domain')  

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'logo': forms.FileInput(attrs={'class': 'form-control'}),
            'email_domain': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g. students.kabianga.ac.ke'
            }),
        }        