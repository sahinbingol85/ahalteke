from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView  # PWA (Mobil uygulama) için eklendi

# İhtiyacımız olan tüm view'ları import ediyoruz
# urls.py dosyasının en üstü
from core.views import index, turnuvalar, rezervasyon_paneli, rezervasyon_sil, manifest_view, cikis_yap, sifre_degistir

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'), # Ana sayfa
    
    # Eski sayfa için yol:
    path('turnuvalar/', turnuvalar, name='turnuvalar'),
    
    # ==========================================
    # KORT REZERVASYON SİSTEMİ (Personel Özel)
    # ==========================================
    path('rezervasyon/', rezervasyon_paneli, name='rezervasyon_paneli'),
    path('rezervasyon/sil/<int:rez_id>/', rezervasyon_sil, name='rezervasyon_sil'),
    # Import listesine cikis_yap ve sifre_degistir eklemeyi unutma!
    path('cikis/', cikis_yap, name='cikis_yap'),
    path('sifre-degistir/', sifre_degistir, name='sifre_degistir'),
    
    # PWA Ayarları (Uygulamayı telefona kurabilmek için)
    path('sw.js', TemplateView.as_view(template_name='core/sw.js', content_type='application/javascript'), name='sw.js'),
    path('manifest_rezervasyon.json', manifest_view, name='manifest_rezervasyon.json'),
]
