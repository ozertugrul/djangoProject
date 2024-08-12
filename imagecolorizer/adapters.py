# adapters.py
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import perform_login
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        user = sociallogin.user
        if user.id:
            return
        try:
            # E-posta adresine göre kullanıcıyı bul
            existing_user = User.objects.get(email=user.email)
            # Eğer kullanıcı bulunduysa, otomatik giriş yap
            sociallogin.connect(request, existing_user)
            perform_login(request, existing_user, 'none')
        except User.DoesNotExist:
            pass