from django.contrib import admin
from .models import Rezervasyon, KapaliDurum, Turnuva, Kategori, Kayit, Mac

# ==========================================
# KORT REZERVASYON ADMİN PANELİ
# ==========================================
@admin.register(Rezervasyon)
class RezervasyonAdmin(admin.ModelAdmin):
    list_display = ('kort', 'tarih', 'saat', 'kisi_adi', 'rezerve_eden', 'olusturulma_tarihi')
    list_filter = ('kort', 'tarih', 'rezerve_eden')
    search_fields = ('kisi_adi', 'aciklama')

@admin.register(KapaliDurum)
class KapaliDurumAdmin(admin.ModelAdmin):
    list_display = ('tarih', 'kort', 'sebep')
    list_filter = ('tarih', 'kort')
    search_fields = ('sebep',)

# ==========================================
# TURNUVA VE KAYIT ADMİN PANELİ
# ==========================================
@admin.register(Turnuva)
class TurnuvaAdmin(admin.ModelAdmin):
    list_display = ('isim', 'baslangic_tarihi', 'kayit_acik_mi')
    list_filter = ('kayit_acik_mi',)
    search_fields = ('isim',)

@admin.register(Kategori)
class KategoriAdmin(admin.ModelAdmin):
    list_display = ('isim',)
    search_fields = ('isim',)

@admin.register(Kayit)
class KayitAdmin(admin.ModelAdmin):
    # Kayit tablosunun görünmesi için bu bloğun mutlaka olması gerekir
    list_display = ('ad', 'soyad', 'turnuva', 'kategori', 'grup', 'telefon', 'odeme_durumu', 'kayit_tarihi')
    list_editable = ('odeme_durumu', 'grup') # Listeden çıkmadan hızlıca grup ve ödeme düzenleme
    list_filter = ('turnuva', 'kategori', 'grup', 'odeme_durumu')
    search_fields = ('ad', 'soyad', 'telefon')

# ==========================================
# MAÇ (FİKSTÜR) ADMİN PANELİ
# ==========================================
@admin.register(Mac)
class MacAdmin(admin.ModelAdmin):
    # Mac tablosunun görünmesi için bu bloğun mutlaka olması gerekir
    list_display = ('grup', 'kategori', 'oyuncu1', 'oyuncu2', 'tarih', 'saat', 'durum')
    list_editable = ('durum',) # Listeden çıkmadan maç durumunu değiştirme
    list_filter = ('turnuva', 'kategori', 'grup', 'durum', 'tarih')
    search_fields = ('oyuncu1__ad', 'oyuncu1__soyad', 'oyuncu2__ad', 'oyuncu2__soyad', 'grup')
    ordering = ('-tarih', '-saat')