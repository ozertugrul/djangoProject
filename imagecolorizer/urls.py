from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.index, name='index'),
    path('mygallery/', views.mygallery, name='mygallery'),
    path('account/', views.account, name='account'),
    path('setting/', views.setting, name='setting'),
    path('signup/', views.signup, name='signup'),
    path('user_login/', views.user_login, name='login'),
    path('editor/<int:image_id>/', views.editor, name='editor'),
    path('check_email/', views.check_email, name='check_email'),
    path('homepage/', views.homepage, name='homepage'),
    path('logout/', views.logout, name='logout'),
    path('sologin/', views.sologin, name='sologin'),
    path('decrease_credit/', views.decrease_credit, name='decrease_credit'),
    path('iyzico-payment/', views.iyzico_payment, name='iyzico_payment'),
    path('redeem-coupon/', views.redeem_coupon, name='redeem_coupon'), 
    path('change_pass/', views.change_password, name='change_password'),
    path('delete_account/', views.delete_account, name='delete_account'),
    path('initiate-payment/', views.initiate_payment, name='initiate_payment'),
    path('payment-callback/', views.payment_callback, name='payment_callback'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)