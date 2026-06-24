import json
import random
import re  # EKLENDİ: Telefon numarası temizliği için
from itertools import combinations
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
import unicodedata

from django.core.mail import send_mail
from django.conf import settings
from django.utils.crypto import get_random_string

from .models import Rezervasyon, KapaliDurum, Turnuva, Kategori, Kayit, Mac
from .forms import KayitForm

# --- YARDIMCI FONKSİYON: Türkçe Ay İsimleri ---
def turkce_tarih_format(tarih):
    aylar = ["", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    return f"{tarih.day} {aylar[tarih.month]} {tarih.year}"

# --- YARDIMCI FONKSİYON: ATP Puan Durumu Hesaplama ---
def puan_durumu_hesapla(grup_adi, kategori, turnuva):
    oyuncular = Kayit.objects.filter(turnuva=turnuva, kategori=kategori, grup=grup_adi)
    maclar = Mac.objects.filter(turnuva=turnuva, kategori=kategori, grup=grup_adi)
    
    istatistikler = []
    for oyuncu in oyuncular:
        stat = {
            'oyuncu': oyuncu,
            'oynadi': 0, 'galibiyet': 0, 'maglubiyet': 0,
            'aldigi_set': 0, 'verdigi_set': 0,
            'aldigi_oyun': 0, 'verdigi_oyun': 0
        }
        
        oynanan_maclar = maclar.filter(Q(oyuncu1=oyuncu) | Q(oyuncu2=oyuncu), durum='oynandi')
        
        for mac in oynanan_maclar:
            if 'BAY' in mac.oyuncu1.ad.upper() or 'BAY' in mac.oyuncu2.ad.upper():
                continue
                
            stat['oynadi'] += 1
            is_oyuncu1 = (mac.oyuncu1 == oyuncu)
            
            # Galibiyet hesabı
            if hasattr(mac, 'kazanan') and mac.kazanan == oyuncu:
                stat['galibiyet'] += 1
            else:
                stat['maglubiyet'] += 1
                
            if mac.set1_oyuncu1 is not None and mac.set1_oyuncu2 is not None:
                if is_oyuncu1:
                    stat['aldigi_oyun'] += mac.set1_oyuncu1
                    stat['verdigi_oyun'] += mac.set1_oyuncu2
                    if mac.set1_oyuncu1 > mac.set1_oyuncu2: stat['aldigi_set'] += 1
                    elif mac.set1_oyuncu1 < mac.set1_oyuncu2: stat['verdigi_set'] += 1
                else:
                    stat['aldigi_oyun'] += mac.set1_oyuncu2
                    stat['verdigi_oyun'] += mac.set1_oyuncu1
                    if mac.set1_oyuncu2 > mac.set1_oyuncu1: stat['aldigi_set'] += 1
                    elif mac.set1_oyuncu2 < mac.set1_oyuncu1: stat['verdigi_set'] += 1
                    
            if mac.set2_oyuncu1 is not None and mac.set2_oyuncu2 is not None:
                if is_oyuncu1:
                    stat['aldigi_oyun'] += mac.set2_oyuncu1
                    stat['verdigi_oyun'] += mac.set2_oyuncu2
                    if mac.set2_oyuncu1 > mac.set2_oyuncu2: stat['aldigi_set'] += 1
                    elif mac.set2_oyuncu1 < mac.set2_oyuncu2: stat['verdigi_set'] += 1
                else:
                    stat['aldigi_oyun'] += mac.set2_oyuncu2
                    stat['verdigi_oyun'] += mac.set2_oyuncu1
                    if mac.set2_oyuncu2 > mac.set2_oyuncu1: stat['aldigi_set'] += 1
                    elif mac.set2_oyuncu2 < mac.set2_oyuncu1: stat['verdigi_set'] += 1
                    
            if mac.set3_oyuncu1 is not None and mac.set3_oyuncu2 is not None:
                if is_oyuncu1:
                    if mac.set3_oyuncu1 > mac.set3_oyuncu2:
                        stat['aldigi_set'] += 1
                        stat['aldigi_oyun'] += 1
                    elif mac.set3_oyuncu1 < mac.set3_oyuncu2:
                        stat['verdigi_set'] += 1
                        stat['verdigi_oyun'] += 1
                else:
                    if mac.set3_oyuncu2 > mac.set3_oyuncu1:
                        stat['aldigi_set'] += 1
                        stat['aldigi_oyun'] += 1
                    elif mac.set3_oyuncu2 < mac.set3_oyuncu1:
                        stat['verdigi_set'] += 1
                        stat['verdigi_oyun'] += 1
                        
        istatistikler.append(stat)
        
    istatistikler.sort(key=lambda x: (
        x['galibiyet'], 
        (x['aldigi_set'] - x['verdigi_set']), 
        (x['aldigi_oyun'] - x['verdigi_oyun'])
    ), reverse=True)
    
    return istatistikler


# --- YARDIMCI FONKSİYON: Türkçe Karakterleri İngilizceye Çevirme (Username için) ---
def slugify_turkce(text):
    text = text.replace('ı', 'i').replace('İ', 'I')
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()


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
            
            if kayit.telefon:
                kayit.telefon = kayit.telefon.replace(" ", "").strip()
            
            if kayit.ad:
                kayit.ad = kayit.ad.strip().title()
            if kayit.soyad:
                kayit.soyad = kayit.soyad.strip().title()
            
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
                    <strong>IBAN:</strong> TR75 0006 7010 0000 0200 0474 74
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
    if not request.user.is_staff:
        messages.error(request, 'Erişim Engellendi: Bu sayfaya sadece yetkili kulüp personeli erişebilir!')
        return redirect('profil')
        
    aktif_turnuva = Turnuva.objects.order_by('-id').first()
    
    if request.method == 'POST':
        # YENİ EKLENEN: OTOMATİK ŞİFRE OLUŞTURMA İŞLEMİ (Telefon Numarası ile)
        if 'otomatik_sifre_olustur' in request.POST:
            onayli_oyuncular = Kayit.objects.filter(turnuva=aktif_turnuva, odeme_durumu='onaylandi')
            olusturulan_hesap_sayisi = 0
            
            for oyuncu in onayli_oyuncular:
                if 'BAY' in oyuncu.ad.upper():
                    continue
                    
                # Telefon numarasından tüm boşluk, tire, parantez gibi karakterleri sil
                temiz_telefon = re.sub(r'\D', '', oyuncu.telefon) if oyuncu.telefon else None
                
                # Eğer kullanıcının numarası yoksa (olmamalı ama önlem) atla
                if not temiz_telefon:
                    continue
                    
                # Eğer bu telefon numarasıyla daha önce açılmışsa geç
                if User.objects.filter(username=temiz_telefon).exists():
                    continue
                    
                # Kullanıcıyı oluştur (Kullanıcı Adı: Temiz Telefon, Şifre: Ahal2026!)
                yeni_user = User.objects.create_user(
                    username=temiz_telefon,
                    password='Ahal2026!',
                    first_name=oyuncu.ad,
                    last_name=oyuncu.soyad
                )
                olusturulan_hesap_sayisi += 1
                
            messages.success(request, f"İşlem Tamam! {olusturulan_hesap_sayisi} adet oyuncuya otomatik telefon numarasıyla giriş oluşturuldu. (Standart Şifre: Ahal2026!)")
            return redirect('yonetim_paneli')

        elif 'manuel_kayit' in request.POST:
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

        elif 'odeme_guncelle' in request.POST:
            kayit_id = request.POST.get('kayit_id')
            yeni_durum = request.POST.get('odeme_durumu')
            if kayit_id and yeni_durum:
                kayit = get_object_or_404(Kayit, id=kayit_id)
                kayit.odeme_durumu = yeni_durum
                kayit.save()
                messages.success(request, f"Güncellendi: {kayit.ad} {kayit.soyad} ödeme durumu '{kayit.get_odeme_durumu_display()}' yapıldı.")
                donus_url = request.META.get('HTTP_REFERER', '/yonetim-paneli/')
                return redirect(donus_url)

    form = KayitForm()
    tum_kategoriler = Kategori.objects.all()
    secilen_kategoriler = request.GET.getlist('kategori_filtre')
    
    genel_kayitlar = Kayit.objects.filter(turnuva=aktif_turnuva) if aktif_turnuva else []
    kayitlar = genel_kayitlar.order_by('-kayit_tarihi')
    
    if secilen_kategoriler:
        kayitlar = kayitlar.filter(kategori__id__in=secilen_kategoriler)
        
    toplam_kayit = genel_kayitlar.count() if aktif_turnuva else 0
    onaylananlar = genel_kayitlar.filter(odeme_durumu='onaylandi').count() if aktif_turnuva else 0
    bekleyenler = genel_kayitlar.filter(odeme_durumu='bekliyor').count() if aktif_turnuva else 0
    
    kategori_istatistikleri = []
    if aktif_turnuva:
        kategori_istatistikleri = genel_kayitlar.values('kategori__isim').annotate(toplam=Count('id')).order_by('-toplam')

    context = {
        'aktif_turnuva': aktif_turnuva,
        'form': form,
        'kayitlar': kayitlar,
        'toplam_kayit': toplam_kayit,
        'onaylananlar': onaylananlar,
        'bekleyenler': bekleyenler,
        'kategori_istatistikleri': kategori_istatistikleri,
        'tum_kategoriler': tum_kategoriler,
        'secilen_kategoriler': [int(i) for i in secilen_kategoriler if i.isdigit()],
    }
    return render(request, 'core/yonetim_paneli.html', context)


# ==========================================
# PANEL OYUNCU SİLME AKSİYONU
# ==========================================
@login_required(login_url='/giris/')
def kayit_sil(request, kayit_id):
    if not request.user.is_staff:
        messages.error(request, 'Bu işlem için yetkiniz yok.')
        return redirect('profil')
        
    kayit = get_object_or_404(Kayit, id=kayit_id)
    oyuncu_adi = f"{kayit.ad} {kayit.soyad}"
    kayit.delete()
    
    messages.success(request, f"Sistem Notu: {oyuncu_adi} isimli oyuncunun kaydı listeden tamamen silindi.")
    donus_url = request.META.get('HTTP_REFERER', '/yonetim-paneli/')
    return redirect(donus_url)


# ==========================================
# CANLI YAYIN: KURA ÇEKİM MODÜLÜ
# ==========================================
@login_required(login_url='/giris/')
def kura_cekimi(request):
    if not request.user.is_staff:
        messages.error(request, 'Yetkisiz erişim.')
        return redirect('profil')
        
    aktif_turnuva = Turnuva.objects.order_by('-id').first()
    
    onayli_kayitlar = Kayit.objects.filter(turnuva=aktif_turnuva, odeme_durumu='onaylandi')
    
    kategori_oyunculari = {}
    kategoriler = Kategori.objects.all()
    
    for k in kategoriler:
        oyuncular = list(onayli_kayitlar.filter(kategori=k).values('id', 'ad', 'soyad', 'grup'))
        if oyuncular:
            kategori_oyunculari[k.id] = {
                'kategori_isim': k.isim,
                'oyuncular': oyuncular
            }
            
    context = {
        'aktif_turnuva': aktif_turnuva,
        'kategori_oyunculari_json': json.dumps(kategori_oyunculari),
        'kategoriler': kategoriler
    }
    return render(request, 'core/kura_cekimi.html', context)

@login_required(login_url='/giris/')
def kura_kaydet(request):
    if request.method == 'POST' and request.user.is_staff:
        try:
            data = json.loads(request.body)
            for item in data:
                kayit = Kayit.objects.get(id=item['id'])
                kayit.grup = item['grup']
                kayit.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'invalid'})


# ==========================================
# FİKSTÜR OLUŞTURMA (OTOMATİK EŞLEŞTİRME)
# ==========================================
@login_required(login_url='/giris/')
def fikstur_olustur(request):
    if not request.user.is_staff:
        return redirect('profil')
        
    aktif_turnuva = Turnuva.objects.order_by('-id').first()
    if not aktif_turnuva:
        messages.error(request, "Aktif turnuva bulunamadı.")
        return redirect('yonetim_paneli')

    kategoriler = Kategori.objects.all()
    olusturulan_mac_sayisi = 0

    for kat in kategoriler:
        oyuncular = Kayit.objects.filter(turnuva=aktif_turnuva, kategori=kat, odeme_durumu='onaylandi').exclude(grup__isnull=True).exclude(grup='')
        
        gruplar_dict = {}
        for o in oyuncular:
            if o.grup not in gruplar_dict:
                gruplar_dict[o.grup] = []
            gruplar_dict[o.grup].append(o)
            
        for grup_adi, grup_oyunculari in gruplar_dict.items():
            varsa_mac = Mac.objects.filter(turnuva=aktif_turnuva, kategori=kat, grup=grup_adi).exists()
            if varsa_mac:
                continue
                
            eslesmeler = list(combinations(grup_oyunculari, 2))
            
            if len(grup_oyunculari) == 4:
                eslesmeler = [eslesmeler[0], eslesmeler[5], eslesmeler[1], eslesmeler[4], eslesmeler[2], eslesmeler[3]]
            elif len(grup_oyunculari) == 3:
                eslesmeler = [eslesmeler[0], eslesmeler[2], eslesmeler[1]]
            else:
                random.shuffle(eslesmeler)
            
            for oyuncu1, oyuncu2 in eslesmeler:
                Mac.objects.create(
                    turnuva=aktif_turnuva,
                    kategori=kat,
                    grup=grup_adi,
                    oyuncu1=oyuncu1,
                    oyuncu2=oyuncu2,
                    durum='planlaniyor'
                )
                olusturulan_mac_sayisi += 1

    if olusturulan_mac_sayisi > 0:
        messages.success(request, f"Harika! {olusturulan_mac_sayisi} adet maç eşleşmesi mükemmel dağılımla oluşturuldu.")
    else:
        messages.warning(request, "Yeni eşleşme oluşturulmadı. (Tüm kuralar zaten eşleştirilmiş olabilir).")
        
    return redirect('fikstur_yonetimi')


# ==========================================
# FİKSTÜR YÖNETİM PANELİ (TARİH/SAAT GİRİŞİ)
# ==========================================
@login_required(login_url='/giris/')
def fikstur_yonetimi(request):
    if not request.user.is_staff:
        return redirect('profil')
        
    aktif_turnuva = Turnuva.objects.order_by('-id').first()
    
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            mac_id = data.get('mac_id')
            tarih = data.get('tarih')
            saat = data.get('saat')
            kort = data.get('kort')
            
            mac = Mac.objects.get(id=mac_id)
            if tarih: mac.tarih = tarih
            else: mac.tarih = None
                
            if saat: mac.saat = saat
            else: mac.saat = None
                
            if kort: mac.kort = kort
            else: mac.kort = None
            
            if mac.tarih and mac.saat:
                mac.durum = 'bekliyor'
            else:
                mac.durum = 'planlaniyor'
                
            mac.save()
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

    maclar = Mac.objects.filter(turnuva=aktif_turnuva).order_by('kategori', 'grup', 'id')
    kategoriler = Kategori.objects.all()
    
    secilen_kat = request.GET.get('kategori_filtre')
    if secilen_kat:
        maclar = maclar.filter(kategori__id=secilen_kat)
        
    planlanmamis_maclar = maclar.filter(durum='planlaniyor')
    planlanmis_maclar = maclar.filter(durum__in=['bekliyor', 'oynandi'])
        
    context = {
        'aktif_turnuva': aktif_turnuva,
        'planlanmamis_maclar': planlanmamis_maclar,
        'planlanmis_maclar': planlanmis_maclar,
        'kategoriler': kategoriler,
        'secilen_kat': int(secilen_kat) if secilen_kat else ''
    }
    return render(request, 'core/fikstur_yonetimi.html', context)


# ==========================================
# FİKSTÜRÜ KOMPLE SIFIRLAMA
# ==========================================
@login_required(login_url='/giris/')
def fikstur_sifirla(request):
    if not request.user.is_staff:
        return redirect('profil')
        
    if request.method == 'POST':
        aktif_turnuva = Turnuva.objects.order_by('-id').first()
        if aktif_turnuva:
            silinen_sayi, _ = Mac.objects.filter(turnuva=aktif_turnuva).delete()
            messages.success(request, f"Tüm fikstür başarıyla sıfırlandı! (Silinen eşleşme: {silinen_sayi})")
            
    return redirect('fikstur_yonetimi')


# ==========================================
# HAKEM SİSTEMİ: CANLI SKOR GİRİŞİ
# ==========================================
@login_required(login_url='/giris/')
def hakem_canli_skor(request):
    if not request.user.is_staff:
        messages.error(request, 'Bu sayfaya erişim yetkiniz yok.')
        return redirect('profil')
        
    aktif_turnuva = Turnuva.objects.order_by('-id').first()
    
    if request.method == 'POST':
        mac_id = request.POST.get('mac_id')
        if mac_id:
            mac = get_object_or_404(Mac, id=mac_id)
            
            set1_o1 = request.POST.get('set1_o1')
            set1_o2 = request.POST.get('set1_o2')
            set1_tb1 = request.POST.get('set1_tb1')
            set1_tb2 = request.POST.get('set1_tb2')
            
            set2_o1 = request.POST.get('set2_o1')
            set2_o2 = request.POST.get('set2_o2')
            set2_tb1 = request.POST.get('set2_tb1')
            set2_tb2 = request.POST.get('set2_tb2')
            
            set3_o1 = request.POST.get('set3_o1')
            set3_o2 = request.POST.get('set3_o2')

            skor1_str = ""
            skor2_str = ""
            
            if set1_o1 and set1_o2:
                skor1_str += f"{set1_o1}"
                skor2_str += f"{set1_o2}"
                if set1_tb1 or set1_tb2:
                    skor1_str += f"({set1_tb1 or 0})"
                    skor2_str += f"({set1_tb2 or 0})"
            
            if set2_o1 and set2_o2:
                skor1_str += f", {set2_o1}"
                skor2_str += f", {set2_o2}"
                if set2_tb1 or set2_tb2:
                    skor1_str += f"({set2_tb1 or 0})"
                    skor2_str += f"({set2_tb2 or 0})"
                    
            if set3_o1 and set3_o2:
                skor1_str += f", [{set3_o1}]"
                skor2_str += f", [{set3_o2}]"

            mac.skor1 = skor1_str
            mac.skor2 = skor2_str
            mac.durum = 'oynandi'
            
            mac.save()
            messages.success(request, f"Skor başarıyla kaydedildi: {mac.oyuncu1.ad} vs {mac.oyuncu2.ad}")
            return redirect('hakem')

    bekleyen_maclar = Mac.objects.filter(turnuva=aktif_turnuva, durum='bekliyor').order_by('tarih', 'saat', 'kategori')

    context = {
        'bekleyen_maclar': bekleyen_maclar
    }
    return render(request, 'core/hakem.html', context)


# ==========================================
# GENEL ZİYARETÇİ: FİKSTÜR GÖRÜNÜMÜ
# ==========================================
def fikstur(request):
    aktif_turnuva = Turnuva.objects.order_by('-id').first()
    kategoriler = Kategori.objects.all() if aktif_turnuva else []
    
    secili_kategori = None
    gruplar_verisi = []
    
    kat_id = request.GET.get('kategori')
    if kat_id:
        secili_kategori = Kategori.objects.filter(id=kat_id).first()
    elif kategoriler:
        secili_kategori = kategoriler.first()
        
    if secili_kategori and aktif_turnuva:
        grup_isimleri = Kayit.objects.filter(turnuva=aktif_turnuva, kategori=secili_kategori).exclude(grup__isnull=True).exclude(grup='').values_list('grup', flat=True).distinct()
        
        for grup_adi in grup_isimleri:
            istatistikler = puan_durumu_hesapla(grup_adi, secili_kategori, aktif_turnuva)
            grup_maclari = Mac.objects.filter(turnuva=aktif_turnuva, kategori=secili_kategori, grup=grup_adi).order_by('tarih', 'saat')
            
            gruplar_verisi.append({
                'grup_ismi': grup_adi,
                'oyuncular': istatistikler,
                'maclar': grup_maclari
            })
            
    context = {
        'kategoriler': kategoriler,
        'secili_kategori': secili_kategori,
        'gruplar_verisi': gruplar_verisi,
    }
    return render(request, 'core/fikstur.html', context)


# ==========================================
# OYUNCU PROFİLİ (MOBİL PANEL)
# ==========================================
@login_required(login_url='/giris/')
def profil(request):
    oyuncu = Kayit.objects.filter(
        ad__iexact=request.user.first_name,
        soyad__iexact=request.user.last_name
    ).order_by('-id').first()
    
    if not oyuncu:
        return render(request, 'core/oyuncu_paneli.html', {'mesaj': 'Henüz bir turnuvaya kayıtlı değilsiniz veya hesabınız eşleşmedi. Lütfen yönetimle iletişime geçin.'})

    oyuncunun_grubu = oyuncu.grup
    kategori = oyuncu.kategori
    aktif_turnuva = oyuncu.turnuva
    
    oyuncu_maclari = Mac.objects.filter(Q(oyuncu1=oyuncu) | Q(oyuncu2=oyuncu))
    bekleyen_maclar = oyuncu_maclari.filter(durum__in=['planlaniyor', 'bekliyor']).order_by('tarih', 'saat')
    gecmis_maclar = oyuncu_maclari.filter(durum='oynandi').order_by('-tarih', '-saat')
    
    tum_gruplar_verisi = []
    
    if kategori and aktif_turnuva:
        grup_isimleri = Kayit.objects.filter(turnuva=aktif_turnuva, kategori=kategori).exclude(grup__isnull=True).exclude(grup='').values_list('grup', flat=True).distinct()
        
        for grup_adi in grup_isimleri:
            istatistikler = puan_durumu_hesapla(grup_adi, kategori, aktif_turnuva)
            grup_maclari = Mac.objects.filter(turnuva=aktif_turnuva, kategori=kategori, grup=grup_adi).order_by('tarih', 'saat')
            
            tum_gruplar_verisi.append({
                'grup': {'isim': grup_adi}, 
                'istatistikler': istatistikler,
                'maclar': grup_maclari,
                'is_kendi_grubu': (grup_adi == oyuncunun_grubu)
            })

    context = {
        'oyuncu': oyuncu,
        'oyuncunun_grubu': {'isim': oyuncunun_grubu} if oyuncunun_grubu else None,
        'bekleyen_maclar': bekleyen_maclar,
        'gecmis_maclar': gecmis_maclar,
        'tum_gruplar_verisi': tum_gruplar_verisi,
    }
    return render(request, 'core/oyuncu_paneli.html', context)


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
