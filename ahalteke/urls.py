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
    path('giris/', auth_views.LoginView.as_view(template_name='core/login.html'), name='giris'), 
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    
    path('cikis/', views.cikis_yap, name='cikis_yap'),
    path('logout/', views.cikis_yap, name='logout'),
    
    # ==========================================
    # TURNUVA VE OYUNCU PROFİLİ
    # ==========================================
    path('turnuvalar/', views.turnuvalar, name='turnuvalar'),
    path('profil/', views.profil, name='profil'),
    
    # EMRE HOCA YÖNETİM PANELİ
    path('yonetim_paneli/', views.yonetim_paneli, name='yonetim_paneli'),
    path('yonetim_paneli/sil/<int:kayit_id>/', views.kayit_sil, name='kayit_sil'),
    
    # KURA ÇEKİM MODÜLÜ
    path('yonetim_paneli/kura-cekimi/', views.kura_cekimi, name='kura_cekimi'),
    path('yonetim_paneli/kura-kaydet/', views.kura_kaydet, name='kura_kaydet'),
    
    # ==========================================
    # FİKSTÜR, MAÇ VE ELEME TABLOSU YÖNETİMİ
    # ==========================================
    path('fikstur/', views.fikstur, name='fikstur'), 
    
    path('yonetim_paneli/fikstur-olustur/', views.fikstur_olustur, name='fikstur_olustur'),
    path('yonetim_paneli/fikstur-yonetimi/', views.fikstur_yonetimi, name='fikstur_yonetimi'),
    path('yonetim_paneli/fikstur-sifirla/', views.fikstur_sifirla, name='fikstur_sifirla'),
    
    # YENİ: ANA TABLO (ELEME) YOLLARI
    path('yonetim_paneli/eleme-olustur/', views.eleme_tablosu_olustur, name='eleme_olustur'),
    path('yonetim_paneli/eleme-sifirla/', views.eleme_tablosu_sifirla, name='eleme_sifirla'),
    path('yonetim_paneli/eleme-yayinla/', views.eleme_yayinla_toggle, name='eleme_yayinla_toggle'),
    
    # HAKEM SİSTEMİ (Canlı Skor ve İptal/Düzeltme)
    path('yonetim_paneli/hakem/', views.hakem_canli_skor, name='hakem'),

    # ==========================================
    # KORT REZERVASYON & MUHASEBE
    # ==========================================
    path('rezervasyon/', views.rezervasyon_paneli, name='rezervasyon_paneli'),
    path('rezervasyon/sil/<int:rez_id>/', views.rezervasyon_sil, name='rezervasyon_sil'),
    path('sifre-degistir/', views.sifre_degistir, name='sifre_degistir'),
    path('muhasebe/', views.muhasebe_paneli, name='muhasebe_paneli'),
    
    # ==========================================
    # PWA (OFFLINE) DOSYALARI & MANIFESTLER
    # ==========================================
    path('manifest_rezervasyon.json', views.manifest_view, name='manifest_rezervasyon.json'),
    path('sw.js', TemplateView.as_view(template_name='core/sw.js', content_type='application/javascript'), name='sw.js'),
    
    path('manifest_hakem.json', TemplateView.as_view(template_name='core/manifest_hakem.json', content_type='application/json'), name='manifest_hakem'),
    path('manifest_oyuncu.json', TemplateView.as_view(template_name='core/manifest_oyuncu.json', content_type='application/json'), name='manifest_oyuncu'),
]