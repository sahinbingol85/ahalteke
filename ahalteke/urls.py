from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views  # Giriş sistemi için eklendi
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    # ÖZEL GİRİŞ SAYFAMIZ
    path('giris/', auth_views.LoginView.as_view(template_name='core/login.html'), name='giris'), 
    path('turnuvalar/', views.turnuvalar, name='turnuvalar'),
    path('rezervasyon/', views.rezervasyon_paneli, name='rezervasyon_paneli'),
    path('rezervasyon/sil/<int:rez_id>/', views.rezervasyon_sil, name='rezervasyon_sil'),
    path('cikis/', views.cikis_yap, name='cikis_yap'),
    path('sifre-degistir/', views.sifre_degistir, name='sifre_degistir'),
    # MANIFEST views.py'den ÇEKİLİYOR
    path('manifest_rezervasyon.json', views.manifest_view, name='manifest_rezervasyon.json'),
    path('sw.js', TemplateView.as_view(template_name='core/sw.js', content_type='application/javascript'), name='sw.js'),
]