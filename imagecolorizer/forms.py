# imagecolorizer/forms.py
from django import forms
from .models import UploadedImage
from .models import Coupon

class ImageUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedImage
        fields = ['image']

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
            raise forms.ValidationError("Passwords do not match")
        return cleaned_data
    
class AddCreditsForm(forms.Form):
    email = forms.EmailField(label="Kullanıcı Email")
    credits_to_add = forms.IntegerField(label="Eklenecek Kredi Miktarı", min_value=1)



class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = ['code', 'credits', 'limits']

    def clean_limit(self):
        limit = self.cleaned_data.get('limits')
        if limit <= 0:
            raise forms.ValidationError("Limit must be greater than 0.")
        return limit
