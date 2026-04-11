from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.http import JsonResponse
from django.db.models import Count, Q

from .models import Rezervasyon, KapaliDurum

def index(request):
    return render(request, 'core/index.html')

def turnuvalar(request):
    return render(request, 'core/turnuvalar.html')

@login_required(login_url='/giris/')
def rezervasyon_paneli(request):
    if not request.user.is_staff:
        messages.error(request, 'Bu sayfaya sadece yetkili kulüp personeli erişebilir!')
        return redirect('index')

    # --- İSTATİSTİK HESAPLAMA (Sadece Superuser görebilir) ---
    istatistikler = None
    if request.user.is_superuser:
        bugun = timezone.now().date()
        
        # Ay sınırlarını kesin belirliyoruz (Muhasebe için önemli)
        ay_basi = bugun.replace(day=1)
        if bugun.month == 12:
            ay_sonu = bugun.replace(year=bugun.year+1, month=1, day=1) - timedelta(days=1)
        else:
            ay_sonu = bugun.replace(month=bugun.month+1, day=1) - timedelta(days=1)
            
        # Hafta sınırlarını kesin belirliyoruz (Pazartesi - Pazar)
        hafta_basi = bugun - timedelta(days=bugun.weekday())
        hafta_sonu = hafta_basi + timedelta(days=6)
        
        # Tam doğru tarih aralıklarında filtreleme yapıyoruz
        istatistikler = Rezervasyon.objects.filter(
            tarih__range=[ay_basi, ay_sonu],
            rezerve_eden__is_superuser=False 
        ).values('rezerve_eden__username', 'rezerve_eden__first_name').annotate(
            toplam_bugun=Count('id', filter=Q(tarih=bugun)),
            toplam_hafta=Count('id', filter=Q(tarih__range=[hafta_basi, hafta_sonu])),
            toplam_ay=Count('id')
        ).order_by('-toplam_ay')
    # ---------------------------------------------------------

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

        if not request.user.is_superuser:
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
                    rezerve_eden=request.user,
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

    context = {
        'secili_tarih': secili_tarih,
        'onceki_gun': onceki_gun.strftime('%Y-%m-%d'),
        'sonraki_gun': sonraki_gun.strftime('%Y-%m-%d'),
        'matrix': matrix,
        'istatistikler': istatistikler, 
    }
    return render(request, 'core/rezervasyon.html', context)

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