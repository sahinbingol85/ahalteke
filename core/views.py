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

from .models import Rezervasyon, KapaliDurum

# --- YARDIMCI FONKSİYON: Türkçe Ay İsimleri ---
def turkce_tarih_format(tarih):
    aylar = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    return f"{tarih.day} {aylar[tarih.month]} {tarih.year}"

# ==========================================
# ANA SAYFA VE TURNUVALAR
# ==========================================
def index(request):
    return render(request, 'core/index.html')

def turnuvalar(request):
    return render(request, 'core/turnuvalar.html')

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
        
        # KAYIT EDEN KİŞİ VE NOT BELİRLEME (Muhasebe Tutarlılığı)
        kayit_sahibi = request.user
        
        if request.user.is_superuser:
            hoca_id = request.POST.get('hoca_secimi')
            if hoca_id: # Eğer yönetici bir hoca adına (Özel Ders) giriyorsa
                kayit_sahibi = User.objects.get(id=hoca_id)
                hoca_adi = kayit_sahibi.first_name if kayit_sahibi.first_name else kayit_sahibi.username
                aciklama = f"Özel Ders: {hoca_adi} - {aciklama}" if aciklama else f"Özel Ders: {hoca_adi}"
            # hoca_id yoksa, yani boş bırakıldıysa, yönetici kendi adına (Genel) giriyordur, not aynı kalır.
        else:
            # Normal hoca ise sadece kendi adına özel ders girebilir
            hoca_adi = request.user.first_name if request.user.first_name else request.user.username
            aciklama = f"Özel Ders: {hoca_adi}"

        basarili_kayit_sayisi = 0
        
        for hafta in range(tekrar_hafta):
            hedef_tarih = secili_tarih + timedelta(days=7 * hafta)
            
            # GÜVENLİK: Seçilen gün ve kort kapalıysa o haftayı atla!
            hedef_gun_kapali = KapaliDurum.objects.filter(tarih=hedef_tarih)
            if hedef_gun_kapali.filter(kort='Hepsi').exists() or hedef_gun_kapali.filter(kort=kort_no).exists():
                continue 

            dolu_mu = Rezervasyon.objects.filter(kort=kort_no, tarih=hedef_tarih, saat=saat).exists()
            
            if not dolu_mu:
                Rezervasyon.objects.create(
                    kort=kort_no,
                    tarih=hedef_tarih,
                    saat=saat,
                    rezerve_eden=kayit_sahibi, # Doğru kişiye atanır
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

    # MATRIX (IZGARA) EKRANINI HAZIRLAMA
    gunun_rezervasyonlari = Rezervasyon.objects.filter(tarih=secili_tarih)
    rez_dict = {(r.kort, r.saat): r for r in gunun_rezervasyonlari}

    # O gün için kapalı olan durumları çekiyoruz
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

    # Superuser için aktif hocaların listesini gönderiyoruz (Seçim menüsü için)
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
# MUHASEBE VE İSTATİSTİK SAYFASI (GÜNCELLENDİ)
# ==========================================
@login_required(login_url='/giris/')
def muhasebe_paneli(request):
    if not request.user.is_superuser:
        messages.error(request, "Bu sayfaya erişim yetkiniz yok.")
        return redirect('rezervasyon_paneli')

    # YENİ: URL'den gelen tarihi okuyoruz (Yoksa bugünü alıyoruz)
    tarih_str = request.GET.get('tarih')
    if tarih_str:
        secili_tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date()
    else:
        secili_tarih = timezone.now().date()

    # Bütün hesaplamalar artık bu "secili_tarih" üzerinden yapılacak
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
        # Sorguyu o ayın başına ve sonuna kilitledik
        hoca_dersleri = Rezervasyon.objects.filter(
            rezerve_eden=hoca, 
            tarih__range=[ay_basi, ay_sonu]
        )
        
        rapor.append({
            'isim': hoca.first_name if hoca.first_name else hoca.username,
            'bugun': hoca_dersleri.filter(tarih=secili_tarih).count(),
            'bu_hafta': hoca_dersleri.filter(tarih__range=[hafta_basi, hafta_sonu]).count(),
            'bu_ay': hoca_dersleri.count(),
            'ders_listesi': hoca_dersleri.order_by('-tarih', '-saat')[:10]
        })

    # Muhasebe sayfasında "Dün/Yarın" yerine "Geçen Hafta/Sonraki Hafta" atlamak daha mantıklıdır
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
# DİĞER FONKSİYONLAR
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