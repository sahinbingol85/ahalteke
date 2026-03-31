from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth import logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm

from .models import Rezervasyon

# ==========================================
# ANA SAYFA 
# ==========================================
def index(request):
    # Artık subdomain kontrolü yapmıyoruz, direkt ana sayfayı gösteriyoruz.
    return render(request, 'core/index.html')

# ==========================================
# ESKİ TURNUVALAR SAYFASI (Değişmedi)
# ==========================================
def turnuvalar(request):
    return render(request, 'core/turnuvalar.html')

# ==========================================
# KORT REZERVASYON SİSTEMİ (SADECE PERSONEL)
# ==========================================
# Giriş yapmamış hocaları Django'nun admin girişine yönlendirir
@login_required(login_url='/giris/')
def rezervasyon_paneli(request):
    # GÜVENLİK: Sadece yetkili personel (Hocalar ve Yöneticiler) girebilir
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

        basarili_kayit_sayisi = 0
        
        for hafta in range(tekrar_hafta):
            hedef_tarih = secili_tarih + timedelta(days=7 * hafta)
            
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
                messages.success(request, f"Harika! {tekrar_hafta} haftalık periyot için rezervasyon oluşturuldu.")
            else:
                messages.success(request, "Rezervasyon başarıyla eklendi.")
        else:
            messages.error(request, "Seçilen saatlerde zaten başka bir rezervasyon mevcut!")
            
        return redirect(f'/rezervasyon/?tarih={secili_tarih.strftime("%Y-%m-%d")}')

    # MATRIX (IZGARA) EKRANINI HAZIRLAMA
    gunun_rezervasyonlari = Rezervasyon.objects.filter(tarih=secili_tarih)
    rez_dict = {(r.kort, r.saat): r for r in gunun_rezervasyonlari}

    saat_dilimleri = [f"{s:02d}:00" for s in range(8, 24)]
    kortlar = ['1', '2', '3', '4']
    
    matrix = []
    for saat in saat_dilimleri:
        satir = {
            'saat': saat,
            'saat_bitis': f"{int(saat[:2])+1:02d}:00",
            'kortlar': []
        }
        for kort in kortlar:
            rez = rez_dict.get((kort, saat))
            satir['kortlar'].append({
                'kort_no': kort,
                'durum': 'dolu' if rez else 'bos',
                'rezervasyon': rez 
            })
        matrix.append(satir)

    onceki_gun = secili_tarih - timedelta(days=1)
    sonraki_gun = secili_tarih + timedelta(days=1)

    context = {
        'secili_tarih': secili_tarih,
        'onceki_gun': onceki_gun.strftime('%Y-%m-%d'),
        'sonraki_gun': sonraki_gun.strftime('%Y-%m-%d'),
        'matrix': matrix,
    }
    return render(request, 'core/rezervasyon.html', context)

# ==========================================
# REZERVASYON SİLME FONKSİYONU
# ==========================================
@login_required(login_url='/giris/')
def rezervasyon_sil(request, rez_id):
    if not request.user.is_staff:
        return redirect('index')
        
    rez = get_object_or_404(Rezervasyon, id=rez_id)
    donulecek_tarih = rez.tarih.strftime('%Y-%m-%d')
    rez.delete()
    messages.success(request, "Rezervasyon iptal edildi.")
    return redirect(f'/rezervasyon/?tarih={donulecek_tarih}')

def manifest_view(request):
    data = {
        "name": "Ahal Teke Rezervasyon",
        "short_name": "AT Rezervasyon",
        "start_url": "/giris/",  # DEĞİŞEN KISIM: Uygulama giriş sayfasından başlayacak
        "scope": "/",            # DEĞİŞEN KISIM: Tüm siteyi kapsayacak
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

# ÇIKIŞ YAPMA
def cikis_yap(request):
    logout(request)
    messages.info(request, "Güvenli bir şekilde çıkış yaptınız.")
    return redirect('giris')  # <-- Ana sayfa yerine giriş ekranına yönlendiriyoruz

# ŞİFRE DEĞİŞTİRME
@login_required(login_url='/giris/')
def sifre_degistir(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user) # Şifre değişince oturum kapanmasın
            messages.success(request, 'Şifreniz başarıyla güncellendi!')
            return redirect('rezervasyon_paneli')
        else:
            messages.error(request, 'Lütfen hataları düzeltin.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'core/sifre_degistir.html', {'form': form})