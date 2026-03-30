from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from django.http import JsonResponse
from core import views  # Tek tek fonksiyon çağırmak yerine tüm views'ı alıyoruz

# Manifest için hızlı fonksiyon (Hata payını sıfıra indirmek için)
def manifest_json_direct(request):
    data = {
        "name": "Ahal Teke Rezervasyon",
        "short_name": "AT Rezervasyon",
        "start_url": "/rezervasyon/",
        "display": "standalone",
        "background_color": "#0a2342",
        "theme_color": "#0a2342",
        "icons": [{"src": "https://i.ibb.co/HTPhptVQ/logo.png", "sizes": "512x512", "type": "image/png"}]
    }
    return JsonResponse(data)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),
    path('turnuvalar/', views.turnuvalar, name='turnuvalar'),
    path('rezervasyon/', views.rezervasyon_paneli, name='rezervasyon_paneli'),
    path('rezervasyon/sil/<int:rez_id>/', views.rezervasyon_sil, name='rezervasyon_sil'),
    path('cikis/', views.cikis_yap, name='cikis_yap'),
    path('sifre-degistir/', views.sifre_degistir, name='sifre_degistir'),
    path('manifest_rezervasyon.json', manifest_json_direct, name='manifest_rezervasyon.json'),
    path('sw.js', TemplateView.as_view(template_name='core/sw.js', content_type='application/javascript'), name='sw.js'),
]