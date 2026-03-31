from django.contrib import admin
from .models import Rezervasyon, KapaliDurum

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

# ==========================================
# KAPALI GÜNLER VE TADİLAT ADMİN PANELİ
# ==========================================
@admin.register(KapaliDurum)
class KapaliDurumAdmin(admin.ModelAdmin):
    # Admin listesinde görünecek sütunlar
    list_display = ('tarih', 'kort', 'sebep')
    
    # Sağ tarafta çıkacak filtreleme seçenekleri
    list_filter = ('tarih', 'kort')
    
    # Yukarıdaki arama çubuğunun nerelerde arama yapacağı
    search_fields = ('sebep',)