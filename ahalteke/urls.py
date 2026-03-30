from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView  # PWA (Mobil uygulama) için eklendi

# İhtiyacımız olan tüm view'ları import ediyoruz
from core.views import index, turnuvalar, rezervasyon_paneli, rezervasyon_sil

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
    
    # PWA Ayarları (Uygulamayı telefona kurabilmek için)
    path('sw.js', TemplateView.as_view(template_name='core/sw.js', content_type='application/javascript'), name='sw.js'),
]
