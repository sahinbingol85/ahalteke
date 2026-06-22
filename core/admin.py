from django.contrib import admin
from .models import Rezervasyon, KapaliDurum, Turnuva, Kategori, Kayit

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

# ==========================================
# TURNUVA VE KAYIT ADMİN PANELİ
# ==========================================
@admin.register(Turnuva)
class TurnuvaAdmin(admin.ModelAdmin):
    list_display = ('isim', 'baslangic_tarihi', 'kayit_acik_mi')
    list_filter = ('kayit_acik_mi',)
    search_fields = ('isim',)

admin.site.register(Kategori)

@admin.register(Kayit)
class KayitAdmin(admin.ModelAdmin):
    # Admin listesinde görünecek sütunlar (Grup sütunu tam ortaya eklendi!)
    list_display = ('ad', 'soyad', 'turnuva', 'kategori', 'grup', 'telefon', 'odeme_durumu', 'kayit_tarihi')
    
    # İŞTE SİHİRLİ KOD: Listeden çıkmadan doğrudan değiştirilebilir alanlar!
    list_editable = ('odeme_durumu',)
    
    # Sağ tarafta çıkacak filtreleme seçenekleri (Grup filtreleme kutusu eklendi!)
    list_filter = ('turnuva', 'kategori', 'grup', 'odeme_durumu')
    
    # Yukarıdaki arama çubuğunun nerelerde arama yapacağı
    search_fields = ('ad', 'soyad', 'telefon')