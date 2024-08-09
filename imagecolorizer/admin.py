from django.contrib import admin
from django.contrib.auth.models import User
from .models import UserCredits
from .forms import AddCreditsForm
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Coupon
from .models import CouponUsage

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'credits', 'limits', 'used_count')
    search_fields = ('code',)

@admin.register(CouponUsage)
class CouponUsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'coupon', 'used_on')
    search_fields = ('user__username', 'coupon__code')

class UserCreditsAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'total_credits', 'remaining_credits')
    search_fields = ('user__email',)
    
    def user_email(self, obj):
        return obj.user.email
    
    user_email.short_description = 'Email'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['user'].queryset = User.objects.all().order_by('email')
        return form

    # Adım 1: Toplu kredi ekleme işlemi için action fonksiyonu
    def add_credits(self, request, queryset):
        if 'apply' in request.POST:
            credits_to_add = int(request.POST.get('credits_to_add', 0))
            for user_credits in queryset:
                user_credits.total_credits += credits_to_add
                user_credits.remaining_credits += credits_to_add
                user_credits.save()
            self.message_user(request, f"{credits_to_add} kredi, seçili {queryset.count()} kullanıcıya başarıyla eklendi.")
            return None

        return render(request, 'admin/add_credits_intermediate.html', context={
            'users': queryset
        })

    add_credits.short_description = "Seçili kullanıcılara kredi ekle"

    actions = [add_credits]

    # Adım 2: Özel URL'ler için get_urls metodunu güncelle
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('add-credits/', self.admin_site.admin_view(self.add_credits_view), name='add_credits'),
        ]
        return custom_urls + urls

    # Adım 3: Tekil kullanıcıya kredi ekleme görünümü
    def add_credits_view(self, request):
        if request.method == 'POST':
            form = AddCreditsForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data['email']
                credits_to_add = form.cleaned_data['credits_to_add']
                try:
                    user = User.objects.get(email=email)
                    user_credits, created = UserCredits.objects.get_or_create(user=user)
                    user_credits.total_credits += credits_to_add
                    user_credits.remaining_credits += credits_to_add
                    user_credits.save()
                    messages.success(request, f"{credits_to_add} kredi başarıyla eklendi.")
                    return redirect('..')
                except User.DoesNotExist:
                    form.add_error('email', 'Bu e-posta adresiyle kayıtlı bir kullanıcı bulunamadı.')
        else:
            form = AddCreditsForm()
        
        context = {
            'form': form,
            'title': 'Kredi Ekle',
        }
        return render(request, 'admin/add_credits.html', context)

admin.site.register(UserCredits, UserCreditsAdmin)

