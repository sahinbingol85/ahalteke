from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    
    # ==========================================
    # GİRİŞ / ÇIKIŞ İŞLEMLERİ
    # ==========================================
    # Hem senin eski views.py yönlendirmelerin (giris/cikis_yap) çalışsın, 
    # hem de yeni HTML'lerdeki {% url 'login' %} etiketleri hata vermesin diye çift isimlendirme (köprü) yaptık.
    path('giris/', auth_views.LoginView.as_view(template_name='core/login.html'), name='giris'), 
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    
    path('cikis/', views.cikis_yap, name='cikis_yap'),
    path('logout/', views.cikis_yap, name='logout'),
    
    # ==========================================
    # TURNUVA VE OYUNCU PROFİLİ
    # ==========================================
    path('turnuvalar/', views.turnuvalar, name='turnuvalar'),
    path('profil/', views.profil, name='profil'),
    
    # HTML tasarımlarındaki {% url 'fikstur' %} linkleri Django'yu çökertmesin diye
    # geçici olarak şimdilik ana sayfaya yönlendiren hayalet bir 'fikstur' yolu ekliyoruz.
    path('fikstur/', views.index, name='fikstur'), 

    # ==========================================
    # KORT REZERVASYON & MUHASEBE
    # ==========================================
    path('rezervasyon/', views.rezervasyon_paneli, name='rezervasyon_paneli'),
    path('rezervasyon/sil/<int:rez_id>/', views.rezervasyon_sil, name='rezervasyon_sil'),
    path('sifre-degistir/', views.sifre_degistir, name='sifre_degistir'),
    path('muhasebe/', views.muhasebe_paneli, name='muhasebe_paneli'),
    
    # ==========================================
    # PWA (OFFLINE) DOSYALARI
    # ==========================================
    path('manifest_rezervasyon.json', views.manifest_view, name='manifest_rezervasyon.json'),
    path('sw.js', TemplateView.as_view(template_name='core/sw.js', content_type='application/javascript'), name='sw.js'),
]