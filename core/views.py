from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.db.models import Count, Q
from django.contrib.auth.models import User
from django.utils.safestring import mark_safe
from django.utils.html import escape

from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string

from .models import Rezervasyon, KapaliDurum, Turnuva, Kategori, Kayit
from .forms import KayitForm

# --- YARDIMCI FONKSİYON: Türkçe Ay İsimleri ---
def turkce_tarih_format(tarih):
    aylar = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    return f"{tarih.day} {aylar[tarih.month]} {tarih.year}"

# ==========================================
# ANA SAYFA 
# ==========================================
def index(request):
    return render(request, 'core/index.html')


# ==========================================
# TURNUVALAR VE KAYIT SİSTEMİ
# ==========================================
def turnuvalar(request):
    aktif_turnuvalar = Turnuva.objects.filter(kayit_acik_mi=True)
    aktif_turnuva = aktif_turnuvalar.first() 
    
    if request.method == 'POST':
        form = KayitForm(request.POST)
        if form.is_valid() and aktif_turnuva:
            kayit = form.save(commit=False)
            
            # 1. TELEFON NUMARASINDAKİ TÜM BOŞLUKLARI SİL
            if kayit.telefon:
                kayit.telefon = kayit.telefon.replace(" ", "").strip()
            
            # 2. İSİMLERİ STANDARTLAŞTIR VE BOŞLUKLARI SİL
            if kayit.ad:
                kayit.ad = kayit.ad.strip().title()
            if kayit.soyad:
                kayit.soyad = kayit.soyad.strip().title()
            
            # 3. KUSURSUZ ÇİFT KAYIT KONTROLÜ
            ayni_kayit_var_mi = Kayit.objects.filter(
                turnuva=aktif_turnuva,
                ad=kayit.ad,
                soyad=kayit.soyad,
                telefon=kayit.telefon
            ).exists()
            
            if ayni_kayit_var_mi:
                hata_mesajı = f"Sayın {kayit.ad} {kayit.soyad}, bu bilgiler ile daha önce zaten bir ön kayıt oluşturulmuş! Lütfen ödeme işlemlerinizi tamamlayınız veya yönetimle iletişime geçiniz."
                messages.error(request, hata_mesajı)
                return render(request, 'core/turnuvalar.html', {'form': form, 'aktif_turnuvalar': aktif_turnuvalar})
            
            kayit.turnuva = aktif_turnuva 
            kayit.save() 
            
            ad = escape(kayit.ad)
            soyad = escape(kayit.soyad)

            basari_mesaji = f"""
            <div style="line-height: 1.6; text-align: center;">
                <span style="font-size: 1.25rem;">Harika! Sayın <strong>{ad} {soyad}</strong>, ön kaydınız başarıyla alındı.</span>
                <hr style="margin: 15px auto; width: 60%; border-color: rgba(0,0,0,0.1);">
                Kaydınızın kesinleşmesi ve fikstüre dahil edilebilmeniz için <strong>4.000 TL</strong>'lik turnuva katılım ücretini en geç <strong>24 Haziran</strong>'a kadar aşağıdaki hesaba yatırmanız gerekmektedir:
                <div style="background-color: #ffffff; color: #0a2342; padding: 15px; border-radius: 10px; margin: 20px 0; border: 2px dashed #28a745; font-family: monospace; font-size: 1.15rem;">
                    <strong>Hesap Sahibi:</strong> Rezan Sertkan<br>
                    <strong>IBAN:</strong> TR75 0006 7010 0000 0020 0047 47
                </div>
                <span style="font-size: 0.95rem; color: #6c757d;">
                    <i class="fa-solid fa-circle-info text-warning me-1"></i> Lütfen ödeme açıklamasına <strong>adınızı ve soyadınızı</strong> yazmayı unutmayın.
                </span><br><br>
                <strong>Kortlarda görüşmek üzere, başarılar dileriz! 🎾</strong>
            </div>
            """
            
            messages.success(request, mark_safe(basari_mesaji))
            return redirect('turnuvalar')
    else:
        form = KayitForm()

    context = {
        'form': form,
        'aktif_turnuvalar': aktif_turnuvalar
    }
    return render(request, 'core/turnuvalar.html', context)


# ==========================================
# EMRE HOCA YÖNETİM PANELİ
# ==========================================
@login_required(login_url='/giris/')
def yonetim_paneli(request):
    # KAPI GÜVENLİĞİ: Sadece is_staff (Yönetici/Hoca) olanlar girebilir!
    if not request.user.is_staff:
        messages.error(request, 'Erişim Engellendi: Bu sayfaya sadece yetkili kulüp personeli erişebilir!')
        return redirect('profil')
        
    aktif_turnuva = Turnuva.objects.filter(kayit_acik_mi=True).first()
    
    if request.method == 'POST':
        # MANUEL KAYIT EKLEME
        if 'manuel_kayit' in request.POST:
            form = KayitForm(request.POST)
            if form.is_valid() and aktif_turnuva:
                kayit = form.save(commit=False)
                kayit.turnuva = aktif_turnuva
                
                if kayit.telefon:
                    kayit.telefon = kayit.telefon.replace(" ", "").strip()
                if kayit.ad:
                    kayit.ad = kayit.ad.strip().title()
                if kayit.soyad:
                    kayit.soyad = kayit.soyad.strip().title()
                
                kayit.save()
                messages.success(request, f"Başarılı: {kayit.ad} {kayit.soyad} sisteme manuel olarak eklendi.")
                return redirect('yonetim_paneli')

        # ÖDEME DURUMU GÜNCELLEME
        elif 'odeme_guncelle' in request.POST:
            kayit_id = request.POST.get('kayit_id')
            yeni_durum = request.POST.get('odeme_durumu')
            if kayit_id and yeni_durum:
                kayit = get_object_or_404(Kayit, id=kayit_id)
                kayit.odeme_durumu = yeni_durum
                kayit.save()
                messages.success(request, f"Güncellendi: {kayit.ad} {kayit.soyad} ödeme durumu '{kayit.get_odeme_durumu_display()}' yapıldı.")
                # GET parametreleri (filtreler) kaybolmasın diye geldiği sayfaya geri döndürüyoruz
                donus_url = request.META.get('HTTP_REFERER', '/yonetim-paneli/')
                return redirect(donus_url)

    form = KayitForm()
    
    # ----------------------------------------------------
    # ÇOKLU KATEGORİ FİLTRELEME SİSTEMİ
    # ----------------------------------------------------
    tum_kategoriler = Kategori.objects.all()
    secilen_kategoriler = request.GET.getlist('kategori_filtre') # Seçilenlerin ID listesini alır
    
    # İstatistiklerin filtrelemeden etkilenmemesi için (sol taraf hep genel durumu göstersin diye)
    genel_kayitlar = Kayit.objects.filter(turnuva=aktif_turnuva) if aktif_turnuva else []
    
    # Sağ taraftaki tablo için verileri hazırlama
    kayitlar = genel_kayitlar.order_by('-kayit_tarihi')
    
    if secilen_kategoriler:
        # Eğer filtre seçildiyse, sadece o kategoridekileri tabloya gönder
        kayitlar = kayitlar.filter(kategori__id__in=secilen_kategoriler)
        
    # Sol Taraf İstatistikleri (Hep Tümünü Gösterir)
    toplam_kayit = genel_kayitlar.count() if aktif_turnuva else 0
    onaylananlar = genel_kayitlar.filter(odeme_durumu='onaylandi').count() if aktif_turnuva else 0
    bekleyenler = genel_kayitlar.filter(odeme_durumu='bekliyor').count() if aktif_turnuva else 0
    
    kategori_istatistikleri = []
    if aktif_turnuva:
        kategori_istatistikleri = genel_kayitlar.values('kategori__isim').annotate(toplam=Count('id')).order_by('-toplam')

    context = {
        'aktif_turnuva': aktif_turnuva,
        'form': form,
        'kayitlar': kayitlar, # Filtrelenmiş tablo listesi
        'toplam_kayit': toplam_kayit,
        'onaylananlar': onaylananlar,
        'bekleyenler': bekleyenler,
        'kategori_istatistikleri': kategori_istatistikleri,
        'tum_kategoriler': tum_kategoriler, # Filtre çubuğu için
        'secilen_kategoriler': [int(i) for i in secilen_kategoriler if i.isdigit()], # Tikli kalması için
    }
    return render(request, 'core/yonetim_paneli.html', context)
# ==========================================
# OYUNCU PROFİLİ
# ==========================================
@login_required(login_url='/giris/')
def profil(request):
    # NOT: Modellerden email alanını sildiğimiz için filtreleme iptal edildi.
    # Aksi takdirde site çökerdi.
    kayit_bilgisi = None 

    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Şifreniz başarıyla güncellendi!')
            return redirect('profil')
        else:
            messages.error(request, 'Lütfen aşağıdaki hataları düzeltin.')
    else:
        form = PasswordChangeForm(request.user)

    context = {
        'form': form,
        'kayit': kayit_bilgisi,
        'gecmis_maclar': [],
        'gelecek_maclar': []
    }
    return render(request, 'core/profil.html', context)


# ==========================================
# KORT REZERVASYON SİSTEMİ 
# ==========================================
@login_required(login_url='/giris/')
def rezervasyon_paneli(request):
    if not request.user.is_staff:
        messages.error(request, 'Bu sayfaya sadece yetkili kulüp personeli erişebilir!')
        return redirect('index')

    tarih_str = request.GET.get('tarih')
    if tarih_str:
        secili_tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
    else:
        secili_tarih = timezone.now().date()

    if request.method == 'POST':
        kort_no = request.POST.get('kort')
        saat = request.POST.get('saat')
        kisi_adi = request.POST.get('kisi_adi')
        aciklama = request.POST.get('aciklama')
        tekrar_hafta = int(request.POST.get('tekrar', 1))
        
        kayit_sahibi = request.user
        
        if request.user.is_superuser:
            hoca_id = request.POST.get('hoca_secimi')
            if hoca_id: 
                kayit_sahibi = User.objects.get(id=hoca_id)
                hoca_adi = kayit_sahibi.first_name if kayit_sahibi.first_name else kayit_sahibi.username
                aciklama = f"Özel Ders: {hoca_adi} - {aciklama}" if aciklama else f"Özel Ders: {hoca_adi}"
        else:
            hoca_adi = request.user.first_name if request.user.first_name else request.user.username
            aciklama = f"Özel Ders: {hoca_adi}"

        basarili_kayit_sayisi = 0
        
        for hafta in range(tekrar_hafta):
            hedef_tarih = secili_tarih + timedelta(days=7 * hafta)
            
            hedef_gun_kapali = KapaliDurum.objects.filter(tarih=hedef_tarih)
            if hedef_gun_kapali.filter(kort='Hepsi').exists() or hedef_gun_kapali.filter(kort=kort_no).exists():
                continue 

            dolu_mu = Rezervasyon.objects.filter(kort=kort_no, tarih=hedef_tarih, saat=saat).exists()
            
            if not dolu_mu:
                Rezervasyon.objects.create(
                    kort=kort_no,
                    tarih=hedef_tarih,
                    saat=saat,
                    rezerve_eden=kayit_sahibi,
                    kisi_adi=kisi_adi,
                    aciklama=aciklama
                )
                basarili_kayit_sayisi += 1

        if basarili_kayit_sayisi > 0:
            if tekrar_hafta > 1:
                messages.success(request, f"Harika! {basarili_kayit_sayisi} hafta için rezervasyon oluşturuldu. (Kapalı/Dolu günler atlandı)")
            else:
                messages.success(request, "Rezervasyon başarıyla eklendi.")
        else:
            messages.error(request, "İşlem başarısız! Seçilen saatler dolu veya kort o gün kapalı.")
            
        return redirect(f'/rezervasyon/?tarih={secili_tarih.strftime("%Y-%m-%d")}')

    gunun_rezervasyonlari = Rezervasyon.objects.filter(tarih=secili_tarih)
    rez_dict = {(r.kort, r.saat): r for r in gunun_rezervasyonlari}

    kapali_durumlar = KapaliDurum.objects.filter(tarih=secili_tarih)
    kapali_kortlar = {k.kort: k.sebep for k in kapali_durumlar}
    genel_kapanis = kapali_kortlar.get('Hepsi') 

    saat_dilimleri = [f"{s:02d}:00" for s in range(8, 24)]
    kortlar = ['1', '2', '3', '4']
    
    matrix = []
    for saat in saat_dilimleri:
        satir = {
            'saat': saat,
            'kortlar': []
        }
        for kort in kortlar:
            rez = rez_dict.get((kort, saat))
            sebep = genel_kapanis or kapali_kortlar.get(kort)
            
            if sebep:
                durum = 'kapali'
                gosterilecek_sebep = sebep
            elif rez:
                durum = 'dolu'
                gosterilecek_sebep = None
            else:
                durum = 'bos'
                gosterilecek_sebep = None

            satir['kortlar'].append({
                'kort_no': kort,
                'durum': durum,
                'rezervasyon': rez,
                'sebep': gosterilecek_sebep
            })
        matrix.append(satir)

    onceki_gun = secili_tarih - timedelta(days=1)
    sonraki_gun = secili_tarih + timedelta(days=1)

    hocalar = User.objects.filter(is_staff=True, is_superuser=False) if request.user.is_superuser else None

    context = {
        'secili_tarih': secili_tarih,
        'onceki_gun': onceki_gun.strftime('%Y-%m-%d'),
        'sonraki_gun': sonraki_gun.strftime('%Y-%m-%d'),
        'matrix': matrix,
        'hocalar': hocalar
    }
    return render(request, 'core/rezervasyon.html', context)

# ==========================================
# MUHASEBE VE İSTATİSTİK SAYFASI 
# ==========================================
@login_required(login_url='/giris/')
def muhasebe_paneli(request):
    if not request.user.is_superuser:
        messages.error(request, "Bu sayfaya erişim yetkiniz yok.")
        return redirect('rezervasyon_paneli')

    tarih_str = request.GET.get('tarih')
    if tarih_str:
        secili_tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
    else:
        secili_tarih = timezone.now().date()

    ay_basi = secili_tarih.replace(day=1)
    if secili_tarih.month == 12:
        ay_sonu = secili_tarih.replace(year=secili_tarih.year+1, month=1, day=1) - timedelta(days=1)
    else:
        ay_sonu = secili_tarih.replace(month=secili_tarih.month+1, day=1) - timedelta(days=1)
        
    hafta_basi = secili_tarih - timedelta(days=secili_tarih.weekday())
    hafta_sonu = hafta_basi + timedelta(days=6)
    
    hocalar = User.objects.filter(is_staff=True, is_superuser=False)
    rapor = []

    for hoca in hocalar:
        hoca_dersleri = Rezervasyon.objects.filter(
            rezerve_eden=hoca, 
            tarih__range=[ay_basi, ay_sonu]
        )
        
        rapor.append({
            'isim': hoca.first_name if hoca.first_name else hoca.username,
            'bugun': hoca_dersleri.filter(tarih=secili_tarih).count(),
            'bu_hafta': hoca_dersleri.filter(tarih__range=[hafta_basi, hafta_sonu]).count(),
            'bu_ay': hoca_dersleri.count(),
            'ders_listesi': hoca_dersleri.order_by('-tarih', '-saat')
        })

    onceki_hafta = secili_tarih - timedelta(days=7)
    sonraki_hafta = secili_tarih + timedelta(days=7)

    context = {
        'rapor': rapor,
        'secili_tarih': secili_tarih,
        'onceki_hafta': onceki_hafta.strftime('%Y-%m-%d'),
        'sonraki_hafta': sonraki_hafta.strftime('%Y-%m-%d'),
        'ay_ismi': turkce_tarih_format(secili_tarih).split(' ')[1] + " " + str(secili_tarih.year) + " Özeti",
        'hafta_bilgi': f"{turkce_tarih_format(hafta_basi)} - {turkce_tarih_format(hafta_sonu)} Haftası"
    }
    return render(request, 'core/muhasebe.html', context)

# ==========================================
# REZERVASYON SİLME 
# ==========================================
@login_required(login_url='/giris/')
def rezervasyon_sil(request, rez_id):
    if not request.user.is_superuser:
        messages.error(request, "İptal işlemi için lütfen yönetim ile iletişime geçin.")
        return redirect('rezervasyon_paneli')
        
    rez = get_object_or_404(Rezervasyon, id=rez_id)
    donulecek_tarih = rez.tarih.strftime('%Y-%m-%d')
    rez.delete()
    messages.success(request, "Rezervasyon başarıyla iptal edildi.")
    return redirect(f'/rezervasyon/?tarih={donulecek_tarih}')

# ==========================================
# DİĞER FONKSİYONLAR (PWA, Çıkış, Şifre)
# ==========================================
def manifest_view(request):
    data = {
        "name": "Ahal Teke Rezervasyon",
        "short_name": "AT Rezervasyon",
        "start_url": "/giris/",
        "scope": "/",
        "display": "standalone",
        "background_color": "#f4f6f9",
        "theme_color": "#0a2342",
        "icons": [
            {
                "src": "https://i.ibb.co/HTPhptVQ/logo.png",
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any maskable"
            },
            {
                "src": "https://i.ibb.co/HTPhptVQ/logo.png",
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable"
            }
        ]
    }
    return JsonResponse(data)

def cikis_yap(request):
    logout(request)
    messages.info(request, "Güvenli bir şekilde çıkış yaptınız.")
    return redirect('giris')

@login_required(login_url='/giris/')
def sifre_degistir(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Şifreniz başarıyla güncellendi!')
            return redirect('rezervasyon_paneli')
        else:
            messages.error(request, 'Lütfen hataları düzeltin.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'core/sifre_degistir.html', {'form': form})