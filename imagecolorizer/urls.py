from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [

    path('', views.index, name='index'),
    path('mygallery/', views.mygallery, name='mygallery'),
    path('account/', views.account, name='account'),
    path('editor/', views.editor, name='editor')
    
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)