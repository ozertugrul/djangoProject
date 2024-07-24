# imagecolorizer/forms.py
from django import forms
from .models import Users

class ImageUploadForm(forms.Form):
    image = forms.ImageField(label='Upload a grayscale image')

class UserCreationForm(forms.Form):
    email = forms.EmailField(max_length=70)
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)
    name = forms.CharField(max_length=70)
    surname = forms.CharField(max_length=70)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise forms.ValidationError("Passwords do not matchamk")
        return cleaned_data