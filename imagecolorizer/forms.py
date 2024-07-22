# imagecolorizer/forms.py
from django import forms

class ImageUploadForm(forms.Form):
    image = forms.ImageField(label='Upload a grayscale image')
