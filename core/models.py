from django.db import models
from django.contrib.auth.models import User

# ==========================================
# KORT REZERVASYON SİSTEMİ (SADECE PERSONEL)
# ==========================================
class Rezervasyon(models.Model):
    KORT_SECENEKLERI = [
        ('1', '1 Nolu Kort'),
        ('2', '2 Nolu Kort'),
        ('3', '3 Nolu Kort'),
        ('4', '4 Nolu Kort'),
    ]

    # Sabah 08:00'den Gece 23:00'e kadar 1'er saatlik dilimler
    SAAT_SECENEKLERI = [
        (f"{saat:02d}:00", f"{saat:02d}:00 - {saat+1:02d}:00") for saat in range(8, 24)
    ]

    kort = models.CharField(max_length=2, choices=KORT_SECENEKLERI, verbose_name="Kort")
    tarih = models.DateField(verbose_name="Tarih")
    saat = models.CharField(max_length=10, choices=SAAT_SECENEKLERI, verbose_name="Saat")
    
    rezerve_eden = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="İşlemi Yapan Hoca")
    
    kisi_adi = models.CharField(max_length=100, verbose_name="Oyuncu / Öğrenci Adı")
    aciklama = models.CharField(max_length=255, blank=True, null=True, verbose_name="Not (Özel Ders, Kiralama, Bakım vb.)")
    
    olusturulma_tarihi = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Rezervasyon"
        verbose_name_plural = "Rezervasyonlar"
        unique_together = ('kort', 'tarih', 'saat') # Çifte rezervasyon kalkanı

    def __str__(self):
        return f"Kort {self.kort} | {self.tarih.strftime('%d.%m.%Y')} - {self.saat} | {self.kisi_adi}"

class KapaliDurum(models.Model):
    KORT_SECIMLERI = [
        ('Hepsi', 'Tüm Kulüp Kapalı (Tatil/Hava Durumu)'),
        ('1', 'Kort 1'),
        ('2', 'Kort 2'),
        ('3', 'Kort 3'),
        ('4', 'Kort 4'),
    ]
    
    tarih = models.DateField(verbose_name="Kapanma Tarihi")
    kort = models.CharField(max_length=10, choices=KORT_SECIMLERI, verbose_name="Kapatılacak Kort", default='Hepsi')
    sebep = models.CharField(max_length=100, verbose_name="Sebep (Örn: Yağmur, Kordaj Bakımı, Resmi Tatil)")

    class Meta:
        verbose_name = "Kapalı Gün / Tadilat"
        verbose_name_plural = "Kapalı Günler ve Tadilatlar"

    def __str__(self):
        return f"{self.tarih.strftime('%d.%m.%Y')} | {self.get_kort_display()} | {self.sebep}"


# ==========================================
# TURNUVA KAYIT SİSTEMİ 
# ==========================================
class Turnuva(models.Model):
    isim = models.CharField(max_length=100, verbose_name="Turnuva Adı")
    baslangic_tarihi = models.DateField(verbose_name="Başlangıç Tarihi")
    kayit_acik_mi = models.BooleanField(default=True, verbose_name="Kayıtlar Açık mı?")

    def __str__(self):
        return self.isim
    
    class Meta:
        verbose_name = "Turnuva"
        verbose_name_plural = "Turnuvalar"

class Kategori(models.Model):
    isim = models.CharField(max_length=50, verbose_name="Kategori Adı")
    
    def __str__(self):
        return self.isim

    class Meta:
        verbose_name = "Kategori"
        verbose_name_plural = "Kategoriler"

class Kayit(models.Model):
    ODEME_DURUMU = (
        ('bekliyor', 'Ödeme Bekliyor'),
        ('onaylandi', 'Onaylandı (Kesin Kayıt)'),
    )

    turnuva = models.ForeignKey(Turnuva, on_delete=models.CASCADE, verbose_name="Turnuva")
    kategori = models.ForeignKey(Kategori, on_delete=models.CASCADE, verbose_name="Kategori")
    ad = models.CharField(max_length=50, verbose_name="Ad")
    soyad = models.CharField(max_length=50, verbose_name="Soyad")
    telefon = models.CharField(max_length=15, verbose_name="Telefon Numarası")
    
    # Partner ve Email alanları buradan tamamen kaldırıldı
    
    odeme_durumu = models.CharField(max_length=20, choices=ODEME_DURUMU, default='bekliyor', verbose_name="Ödeme Durumu")
    kayit_tarihi = models.DateTimeField(auto_now_add=True, verbose_name="Kayıt Tarihi")

    def __str__(self):
        return f"{self.ad} {self.soyad} - {self.kategori}"

    class Meta:
        verbose_name = "Oyuncu Kaydı"
        verbose_name_plural = "Oyuncu Kayıtları"