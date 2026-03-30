from django.contrib import admin
from .models import Rezervasyon

# Register your models here.

# ==========================================
# KORT REZERVASYON ADMİN PANELİ
# ==========================================
@admin.register(Rezervasyon)
class RezervasyonAdmin(admin.ModelAdmin):
    # Admin listesinde görünecek sütunlar
    list_display = ('kort', 'tarih', 'saat', 'kisi_adi', 'rezerve_eden', 'olusturulma_tarihi')
    
    # Sağ tarafta çıkacak filtreleme seçenekleri
    list_filter = ('kort', 'tarih', 'rezerve_eden')
    
    # Yukarıdaki arama çubuğunun nerelerde arama yapacağı
    search_fields = ('kisi_adi', 'aciklama')
