from django.contrib import admin
from django.urls import path
# turnuvalar view'ını da import etmeyi unutma:
from core.views import index, turnuvalar

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', index, name='index'), # Ana sayfa
    # Yeni sayfa için yol:
    path('turnuvalar/', turnuvalar, name='turnuvalar'),
]