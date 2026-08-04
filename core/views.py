import json
import random
import re
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
            if (mac.oyuncu1 and 'BAY' in mac.oyuncu1.ad.upper()) or (mac.oyuncu2 and 'BAY' in mac.oyuncu2.ad.upper()):
                continue
                
            stat['oynadi'] += 1
            is_oyuncu1 = (mac.oyuncu1 == oyuncu)
            
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


def slugify_turkce(text):
    text = text.replace('ı', 'i').replace('İ', 'I')
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn').lower()


# ==========================================
# OTOMATİK İLERİ VE GERİ TUR OTOMASYONU
# ==========================================
def ileri_turu_guncelle(mac):
    eleme_sirasi = ["Son 128", "Son 64", "Son 32", "Son 16", "Çeyrek Final", "Yarı Final", "Final"]
    if mac.grup not in eleme_sirasi or not mac.kazanan:
        return
        
    try:
        current_round_idx = eleme_sirasi.index(mac.grup)
        if current_round_idx >= len(eleme_sirasi) - 1:
            return
            
        next_round_name = eleme_sirasi[current_round_idx + 1]
        
        current_round_matches = list(Mac.objects.filter(
            turnuva=mac.turnuva, kategori=mac.kategori, grup=mac.grup
        ).order_by('id'))
        
        if mac not in current_round_matches:
            return
            
        match_idx = current_round_matches.index(mac)
        next_match_idx = match_idx // 2
        is_second_slot = (match_idx % 2 == 1)
        
        next_round_matches = list(Mac.objects.filter(
            turnuva=mac.turnuva, kategori=mac.kategori, grup=next_round_name
        ).order_by('id'))
        
        if next_match_idx < len(next_round_matches):
            next_mac = next_round_matches[next_match_idx]
            if is_second_slot:
                next_mac.oyuncu2 = mac.kazanan
            else:
                next_mac.oyuncu1 = mac.kazanan
            next_mac.save()
            
            if next_mac.oyuncu1 and next_mac.oyuncu2:
                p1_bay = 'BAY' in next_mac.oyuncu1.ad.upper()
                p2_bay = 'BAY' in next_mac.oyuncu2.ad.upper()
                if p1_bay and not p2_bay:
                    next_mac.kazanan = next_mac.oyuncu2
                    next_mac.durum = 'oynandi'
                    next_mac.skor1, next_mac.skor2 = "0", "BAY"
                    next_mac.save()
                    ileri_turu_guncelle(next_mac)
                elif p2_bay and not p1_bay:
                    next_mac.kazanan = next_mac.oyuncu1
                    next_mac.durum = 'oynandi'
                    next_mac.skor1, next_mac.skor2 = "BAY", "0"
                    next_mac.save()
                    ileri_turu_guncelle(next_mac)
    except Exception as e:
        print("İleri tur güncelleme hatası:", e)


def geri_turu_temizle(mac):
    eleme_sirasi = ["Son 128", "Son 64", "Son 32", "Son 16", "Çeyrek Final", "Yarı Final", "Final"]
    if mac.grup not in eleme_sirasi:
        return
    try:
        current_round_idx = eleme_sirasi.index(mac.grup)
        if current_round_idx >= len(eleme_sirasi) - 1:
            return
        next_round_name = eleme_sirasi[current_round_idx + 1]
        
        current_round_matches = list(Mac.objects.filter(
            turnuva=mac.turnuva, kategori=mac.kategori, grup=mac.grup
        ).order_by('id'))
        if mac not in current_round_matches:
            return
            
        match_idx = current_round_matches.index(mac)
        next_match_idx = match_idx // 2
        is_second_slot = (match_idx % 2 == 1)
        
        next_round_matches = list(Mac.objects.filter(
            turnuva=mac.turnuva, kategori=mac.kategori, grup=next_round_name
        ).order_by('id'))
        
        if next_match_idx < len(next_round_matches):
            next_mac = next_round_matches[next_match_idx]
            if is_second_slot:
                next_mac.oyuncu2 = None
            else:
                next_mac.oyuncu1 = None
            next_mac.kazanan = None
            next_mac.durum = 'planlaniyor'
            next_mac.skor1, next_mac.skor2 = None, None
            next_mac.save()
            geri_turu_temizle(next_mac)
    except Exception as e:
        print("Geri tur temizleme hatası:", e)


# ==========================================
# GENEL PAGES (INDEX & TURNUVALAR)
# ==========================================
def index(request):
    return render(request, 'core/index.html')


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
                turnuva=aktif_turnuva, ad=kayit.ad, soyad=kayit.soyad, telefon=kayit.telefon
            ).exists()
            
            if ayni_kayit_var_mi:
                messages.error(request, f"Sayın {kayit.ad} {kayit.soyad}, bu bilgiler ile ön kayıt zaten mevcut!")
                return render(request, 'core/turnuvalar.html', {'form': form, 'aktif_turnuvalar': aktif_turnuvalar})
            
            kayit.turnuva = aktif_turnuva 
            kayit.save() 
            
            ad, soyad = escape(kayit.ad), escape(kayit.soyad)
            basari_mesaji = f"""
            <div style="text-align: center;">
                <span style="font-size: 1.25rem;">Harika! Sayın <strong>{ad} {soyad}</strong>, ön kaydınız alındı.</span>
            </div>
            """
            messages.success(request, mark_safe(basari_mesaji))
            return redirect('turnuvalar')
    else:
        form = KayitForm()

    return render(request, 'core/turnuvalar.html', {'form': form, 'aktif_turnuvalar': aktif_turnuvalar})


# ==========================================
# EMRE HOCA YÖNETİM PANELİ
# ==========================================
@login_required(login_url='/giris/')
def yonetim_paneli(request):
    if not request.user.is_staff:
        messages.error(request, 'Bu sayfaya sadece yetkili kulüp personeli erişebilir!')
        return redirect('profil')
        
    aktif_turnuva = Turnuva.objects.order_by('-id').first()
    
    if request.method == 'POST':
        if 'otomatik_sifre_olustur' in request.POST:
            onayli_oyuncular = Kayit.objects.filter(turnuva=aktif_turnuva, odeme_durumu='onaylandi')
            olusturulan_hesap_sayisi = 0
            
            for oyuncu in onayli_oyuncular:
                if 'BAY' in oyuncu.ad.upper(): continue
                    
                temiz_telefon = re.sub(r'\D', '', oyuncu.telefon) if oyuncu.telefon else None
                if not temiz_telefon or User.objects.filter(username=temiz_telefon).exists(): continue
                    
                User.objects.create_user(
                    username=temiz_telefon, password='Ahal2026!',
                    first_name=oyuncu.ad, last_name=oyuncu.soyad
                )
                olusturulan_hesap_sayisi += 1
                
            messages.success(request, f"{olusturulan_hesap_sayisi} adet oyuncuya otomatik hesap açıldı (Şifre: Ahal2026!).")
            return redirect('yonetim_paneli')

        elif 'manuel_kayit' in request.POST:
            form = KayitForm(request.POST)
            if form.is_valid() and aktif_turnuva:
                kayit = form.save(commit=False)
                kayit.turnuva = aktif_turnuva
                if kayit.telefon: kayit.telefon = kayit.telefon.replace(" ", "").strip()
                if kayit.ad: kayit.ad = kayit.ad.strip().title()
                if kayit.soyad: kayit.soyad = kayit.soyad.strip().title()
                kayit.save()
                messages.success(request, f"{kayit.ad} {kayit.soyad} eklendi.")
                return redirect('yonetim_paneli')

        elif 'odeme_guncelle' in request.POST:
            kayit_id = request.POST.get('kayit_id')
            yeni_durum = request.POST.get('odeme_durumu')
            if kayit_id and yeni_durum:
                kayit = get_object_or_404(Kayit, id=kayit_id)
                kayit.odeme_durumu = yeni_durum
                kayit.save()
                messages.success(request, f"{kayit.ad} {kayit.soyad} ödeme durumu güncellendi.")
                return redirect(request.META.get('HTTP_REFERER', '/yonetim-paneli/'))

    form = KayitForm()
    tum_kategoriler = Kategori.objects.all()
    secilen_kategoriler = request.GET.getlist('kategori_filtre')
    
    # BAY olanları yönetim panelinde listelemiyoruz
    genel_kayitlar = Kayit.objects.filter(turnuva=aktif_turnuva).exclude(grup='BAY') if aktif_turnuva else []
    kayitlar = genel_kayitlar.order_by('-kayit_tarihi')
    
    if secilen_kategoriler:
        kayitlar = kayitlar.filter(kategori__id__in=secilen_kategoriler)
        
    toplam_kayit = genel_kayitlar.count() if aktif_turnuva else 0
    onaylananlar = genel_kayitlar.filter(odeme_durumu='onaylandi').count() if aktif_turnuva else 0
    bekleyenler = genel_kayitlar.filter(odeme_durumu='bekliyor').count() if aktif_turnuva else 0
    
    kategori_istatistikleri = genel_kayitlar.values('kategori__isim').annotate(toplam=Count('id')).order_by('-toplam') if aktif_turnuva else []

    context = {
        'aktif_turnuva': aktif_turnuva, 'form': form, 'kayitlar': kayitlar,
        'toplam_kayit': toplam_kayit, 'onaylananlar': onaylananlar, 'bekleyenler': bekleyenler,
        'kategori_istatistikleri': kategori_istatistikleri, 'tum_kategoriler': tum_kategoriler,
        'secilen_kategoriler': [int(i) for i in secilen_kategoriler if i.isdigit()],
    }
    return render(request, 'core/yonetim_paneli.html', context)


@login_required(login_url='/giris/')
def kayit_sil(request, kayit_id):
    if not request.user.is_staff: return redirect('profil')
    kayit = get_object_or_404(Kayit, id=kayit_id)
    oyuncu_adi = f"{kayit.ad} {kayit.soyad}"
    kayit.delete()
    messages.success(request, f"{oyuncu_adi} silindi.")
    return redirect(request.META.get('HTTP_REFERER', '/yonetim-paneli/'))


@login_required(login_url='/giris/')
def kura_cekimi(request):
    if not request.user.is_staff: return redirect('profil')
    aktif_turnuva = Turnuva.objects.order_by('-id').first()
    # BAY'lar kura ekranında görünmesin
    onayli_kayitlar = Kayit.objects.filter(turnuva=aktif_turnuva, odeme_durumu='onaylandi').exclude(grup='BAY')
    kategori_oyunculari = {}
    kategoriler = Kategori.objects.all()
    
    for k in kategoriler:
        oyuncular = list(onayli_kayitlar.filter(kategori=k).values('id', 'ad', 'soyad', 'grup'))
        if oyuncular:
            kategori_oyunculari[k.id] = {'kategori_isim': k.isim, 'oyuncular': oyuncular}
            
    return render(request, 'core/kura_cekimi.html', {
        'aktif_turnuva': aktif_turnuva,
        'kategori_oyunculari_json': json.dumps(kategori_oyunculari),
        'kategoriler': kategoriler
    })


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
# GRUP FİKSTÜRÜ VE ANA TABLO (ELEME) ÇEKİMİ
# ==========================================
@login_required(login_url='/giris/')
def fikstur_olustur(request):
    if not request.user.is_staff: return redirect('profil')
    aktif_turnuva = Turnuva.objects.order_by('-id').first()
    if not aktif_turnuva: return redirect('yonetim_paneli')

    kategoriler = Kategori.objects.all()
    olusturulan_mac_sayisi = 0

    for kat in kategoriler:
        # BAY grubunu grup maçlarından hariç tutuyoruz
        oyuncular = Kayit.objects.filter(turnuva=aktif_turnuva, kategori=kat, odeme_durumu='onaylandi').exclude(grup__isnull=True).exclude(grup='').exclude(grup='BAY')
        gruplar_dict = {}
        for o in oyuncular:
            if o.grup not in gruplar_dict: gruplar_dict[o.grup] = []
            gruplar_dict[o.grup].append(o)
            
        for grup_adi, grup_oyunculari in gruplar_dict.items():
            if Mac.objects.filter(turnuva=aktif_turnuva, kategori=kat, grup=grup_adi).exists(): continue
            eslesmeler = list(combinations(grup_oyunculari, 2))
            
            if len(grup_oyunculari) == 4:
                eslesmeler = [eslesmeler[0], eslesmeler[5], eslesmeler[1], eslesmeler[4], eslesmeler[2], eslesmeler[3]]
            elif len(grup_oyunculari) == 3:
                eslesmeler = [eslesmeler[0], eslesmeler[2], eslesmeler[1]]
            else:
                random.shuffle(eslesmeler)
            
            for oyuncu1, oyuncu2 in eslesmeler:
                Mac.objects.create(
                    turnuva=aktif_turnuva, kategori=kat, grup=grup_adi,
                    oyuncu1=oyuncu1, oyuncu2=oyuncu2, durum='planlaniyor'
                )
                olusturulan_mac_sayisi += 1

    if olusturulan_mac_sayisi > 0:
        messages.success(request, f"{olusturulan_mac_sayisi} adet grup maçı oluşturuldu.")
    else:
        messages.warning(request, "Yeni eşleşme oluşturulmadı.")
        
    return redirect('fikstur_yonetimi')


@login_required(login_url='/giris/')
def eleme_tablosu_olustur(request):
    if not request.user.is_staff: return redirect('profil')
    aktif_turnuva = Turnuva.objects.order_by('-id').first()
    if not aktif_turnuva: return redirect('yonetim_paneli')

    def get_seeding(p):
        if p == 1: return [1]
        half = get_seeding(p // 2)
        res = []
        for seed in half:
            res.append(seed)
            res.append(p - seed + 1)
        return res

    kategoriler = Kategori.objects.all()
    olusturulan_mac = 0
    eleme_sirasi = ["Son 128", "Son 64", "Son 32", "Son 16", "Çeyrek Final", "Yarı Final", "Final"]

    for kat in kategoriler:
        if Mac.objects.filter(turnuva=aktif_turnuva, kategori=kat, grup__in=eleme_sirasi).exists():
            continue
            
        # BURASI ÇOK ÖNEMLİ: exclude(grup='BAY') ekleyerek sahte grubu oyuncu tablosu sayımından çıkardık!
        kategori_gruplari = Kayit.objects.filter(
            turnuva=aktif_turnuva, kategori=kat
        ).exclude(grup__isnull=True).exclude(grup='').exclude(grup__in=eleme_sirasi).exclude(grup='BAY').values_list('grup', flat=True).distinct()
        
        all_advancing = []
        for g in kategori_gruplari:
            stats = puan_durumu_hesapla(g, kat, aktif_turnuva)
            if len(stats) > 0:
                stats[0]['sira'] = 1
                all_advancing.append(stats[0])
            if len(stats) > 1:
                stats[1]['sira'] = 2
                all_advancing.append(stats[1])
                
        N = len(all_advancing)
        if N == 0: continue
        
        all_advancing.sort(key=lambda x: (
            -x['sira'], 
            x['galibiyet'],
            x['aldigi_set'] - x['verdigi_set'],
            x['aldigi_oyun'] - x['verdigi_oyun']
        ), reverse=True)
        
        players = [x['oyuncu'] for x in all_advancing]
        
        P = 2
        while P < N: P *= 2
            
        bay_player, _ = Kayit.objects.get_or_create(
            turnuva=aktif_turnuva, kategori=kat, ad="BAY", soyad="Geçti",
            defaults={'telefon': '0000', 'odeme_durumu': 'onaylandi', 'grup': 'BAY'}
        )
        
        while len(players) < P:
            players.append(bay_player)
            
        turlar = []
        curr = P
        while curr >= 2:
            if curr == 128: turlar.append("Son 128")
            elif curr == 64: turlar.append("Son 64")
            elif curr == 32: turlar.append("Son 32")
            elif curr == 16: turlar.append("Son 16")
            elif curr == 8: turlar.append("Çeyrek Final")
            elif curr == 4: turlar.append("Yarı Final")
            elif curr == 2: turlar.append("Final")
            curr //= 2

        first_round_name = turlar[0]
        seeds = get_seeding(P)
        
        for i in range(P // 2):
            p1 = players[seeds[2*i] - 1]
            p2 = players[seeds[2*i + 1] - 1]
            
            is_p1_bay = ('BAY' in p1.ad.upper())
            is_p2_bay = ('BAY' in p2.ad.upper())
            
            mac = Mac.objects.create(
                turnuva=aktif_turnuva, kategori=kat, grup=first_round_name,
                oyuncu1=p1, oyuncu2=p2, durum='planlaniyor'
            )
            olusturulan_mac += 1
            
            if is_p1_bay and not is_p2_bay:
                mac.kazanan, mac.durum, mac.skor1, mac.skor2 = p2, 'oynandi', "0", "BAY"
                mac.save()
            elif is_p2_bay and not is_p1_bay:
                mac.kazanan, mac.durum, mac.skor1, mac.skor2 = p1, 'oynandi', "BAY", "0"
                mac.save()
            elif is_p1_bay and is_p2_bay:
                mac.kazanan, mac.durum = p1, 'oynandi'
                mac.save()

        curr_p = P // 2
        for r_name in turlar[1:]:
            curr_p //= 2
            for _ in range(curr_p):
                Mac.objects.create(
                    turnuva=aktif_turnuva, kategori=kat, grup=r_name,
                    oyuncu1=None, oyuncu2=None, durum='planlaniyor'
                )

        first_round_matches = Mac.objects.filter(turnuva=aktif_turnuva, kategori=kat, grup=first_round_name).order_by('id')
        for m in first_round_matches:
            if m.durum == 'oynandi' and m.kazanan:
                ileri_turu_guncelle(m)

    if olusturulan_mac > 0:
        messages.success(request, f"Harika! Gerçek oyuncu sayısına göre (Tam kural) Ana Tablo Kurası çekildi.")
    else:
        messages.warning(request, "Ana tablo kurası zaten çekilmiş.")
        
    return redirect('fikstur_yonetimi')


@login_required(login_url='/giris/')
def eleme_yayinla_toggle(request):
    if not request.user.is_staff: return redirect('profil')
    aktif_turnuva = Turnuva.objects.order_by('-id').first()
    if aktif_turnuva:
        aktif_turnuva.eleme_yayinlandi = not aktif_turnuva.eleme_yayinlandi
        aktif_turnuva.save()
        durum_str = "yayınlandı ve sitede görünür oldu!" if aktif_turnuva.eleme_yayinlandi else "yayından kaldırıldı (gizlendi)."
        messages.success(request, f"Ana Tablo fikstürü {durum_str}")
    return redirect('fikstur_yonetimi')


@login_required(login_url='/giris/')
def eleme_tablosu_sifirla(request):
    if not request.user.is_staff: return redirect('profil')
    if request.method == 'POST':
        aktif_turnuva = Turnuva.objects.order_by('-id').first()
        if aktif_turnuva:
            eleme_sirasi = ["Son 128", "Son 64", "Son 32", "Son 16", "Çeyrek Final", "Yarı Final", "Final"]
            silinen_sayi, _ = Mac.objects.filter(turnuva=aktif_turnuva, grup__in=eleme_sirasi).delete()
            aktif_turnuva.eleme_yayinlandi = False
            aktif_turnuva.save()
            messages.success(request, f"Ana Tablo kura eşleşmeleri tamamen sıfırlandı!")
    return redirect('fikstur_yonetimi')


@login_required(login_url='/giris/')
def fikstur_yonetimi(request):
    if not request.user.is_staff: return redirect('profil')
    aktif_turnuva = Turnuva.objects.order_by('-id').first()
    eleme_sirasi = ["Son 128", "Son 64", "Son 32", "Son 16", "Çeyrek Final", "Yarı Final", "Final"]
    
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            mac_id = data.get('mac_id')
            tarih = data.get('tarih')
            saat = data.get('saat')
            kort = data.get('kort')
            
            mac = Mac.objects.get(id=mac_id)
            mac.tarih = tarih if tarih else None
            mac.saat = saat if saat else None
            mac.kort = kort if kort else None
            
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
    secilen_grup = request.GET.get('grup_filtre')
    
    mevcut_gruplar = maclar.values_list('grup', flat=True).distinct()
    
    if secilen_kat: 
        maclar = maclar.filter(kategori__id=secilen_kat)
        
    if secilen_grup:
        maclar = maclar.filter(grup=secilen_grup)
        
    secilen_tarih = request.GET.get('tarih_filtre')
    gunun_maclari = Mac.objects.filter(turnuva=aktif_turnuva, tarih=secilen_tarih).order_by('saat', 'kort') if secilen_tarih else []
        
    planlanmamis_maclar = maclar.filter(durum='planlaniyor')
    planlanmis_maclar = maclar.filter(durum__in=['bekliyor', 'oynandi'])

    eleme_maclari = Mac.objects.filter(turnuva=aktif_turnuva, grup__in=eleme_sirasi)
    if secilen_kat:
        eleme_maclari = eleme_maclari.filter(kategori__id=secilen_kat)
    eleme_maclari = eleme_maclari.order_by('id')
        
    return render(request, 'core/fikstur_yonetimi.html', {
        'aktif_turnuva': aktif_turnuva,
        'planlanmamis_maclar': planlanmamis_maclar,
        'planlanmis_maclar': planlanmis_maclar,
        'kategoriler': kategoriler,
        'secilen_kat': int(secilen_kat) if secilen_kat else '',
        'secilen_grup': secilen_grup if secilen_grup else '',
        'mevcut_gruplar': mevcut_gruplar,
        'secilen_tarih': secilen_tarih,
        'gunun_maclari': gunun_maclari,
        'eleme_maclari': eleme_maclari,
    })


@login_required(login_url='/giris/')
def fikstur_sifirla(request):
    if not request.user.is_staff: return redirect('profil')
    if request.method == 'POST':
        aktif_turnuva = Turnuva.objects.order_by('-id').first()
        if aktif_turnuva:
            eleme_sirasi = ["Son 128", "Son 64", "Son 32", "Son 16", "Çeyrek Final", "Yarı Final", "Final"]
            silinen_sayi, _ = Mac.objects.filter(turnuva=aktif_turnuva).exclude(grup__in=eleme_sirasi).delete()
            messages.success(request, f"Tüm GRUP fikstürü sıfırlandı!")
    return redirect('fikstur_yonetimi')


# ==========================================
# HAKEM SİSTEMİ (CANLI SKOR & OTOMATİK İLERLEME)
# ==========================================
@login_required(login_url='/giris/')
def hakem_canli_skor(request):
    if not request.user.is_staff: return redirect('profil')
    aktif_turnuva = Turnuva.objects.order_by('-id').first()
    
    if request.method == 'POST':
        iptal_mac_id = request.POST.get('iptal_mac_id')
        if iptal_mac_id:
            mac = get_object_or_404(Mac, id=iptal_mac_id)
            geri_turu_temizle(mac)
            mac.kazanan = None
            mac.set1_oyuncu1 = mac.set1_oyuncu2 = mac.set1_tb_oyuncu1 = mac.set1_tb_oyuncu2 = None
            mac.set2_oyuncu1 = mac.set2_oyuncu2 = mac.set2_tb_oyuncu1 = mac.set2_tb_oyuncu2 = None
            mac.set3_oyuncu1 = mac.set3_oyuncu2 = None
            mac.skor1 = mac.skor2 = None
            mac.durum = 'bekliyor'
            mac.save()
            messages.success(request, f"{mac.oyuncu1.ad} vs {mac.oyuncu2.ad} skoru sıfırlandı.")
            return redirect('hakem')

        mac_id = request.POST.get('mac_id')
        if mac_id:
            mac = get_object_or_404(Mac, id=mac_id)
            kazanan_id = request.POST.get('kazanan_id')
            if kazanan_id: mac.kazanan_id = kazanan_id
            
            def to_int(value): return int(value) if value and value.isdigit() else None

            mac.set1_oyuncu1 = to_int(request.POST.get('set1_o1'))
            mac.set1_oyuncu2 = to_int(request.POST.get('set1_o2'))
            mac.set1_tb_oyuncu1 = to_int(request.POST.get('set1_tb1'))
            mac.set1_tb_oyuncu2 = to_int(request.POST.get('set1_tb2'))
            
            mac.set2_oyuncu1 = to_int(request.POST.get('set2_o1'))
            mac.set2_oyuncu2 = to_int(request.POST.get('set2_o2'))
            mac.set2_tb_oyuncu1 = to_int(request.POST.get('set2_tb1'))
            mac.set2_tb_oyuncu2 = to_int(request.POST.get('set2_tb2'))
            
            mac.set3_oyuncu1 = to_int(request.POST.get('set3_o1'))
            mac.set3_oyuncu2 = to_int(request.POST.get('set3_o2'))

            o1_set, o2_set = 0, 0
            if mac.set1_oyuncu1 is not None and mac.set1_oyuncu2 is not None:
                if mac.set1_oyuncu1 > mac.set1_oyuncu2: o1_set += 1
                elif mac.set1_oyuncu2 > mac.set1_oyuncu1: o2_set += 1
                
            if mac.set2_oyuncu1 is not None and mac.set2_oyuncu2 is not None:
                if mac.set2_oyuncu1 > mac.set2_oyuncu2: o1_set += 1
                elif mac.set2_oyuncu2 > mac.set2_oyuncu1: o2_set += 1
                
            if mac.set3_oyuncu1 is not None and mac.set3_oyuncu2 is not None:
                if mac.set3_oyuncu1 > mac.set3_oyuncu2: o1_set += 1
                elif mac.set3_oyuncu2 > mac.set3_oyuncu1: o2_set += 1

            mac.skor1, mac.skor2 = str(o1_set), str(o2_set)
            mac.durum = 'oynandi'
            mac.save()
            
            ileri_turu_guncelle(mac)
            
            messages.success(request, f"Skor kaydedildi: {mac.oyuncu1.ad} vs {mac.oyuncu2.ad}")
            return redirect('hakem')

    bekleyen_maclar = Mac.objects.filter(turnuva=aktif_turnuva, durum='bekliyor').order_by('tarih', 'saat', 'kategori')
    tamamlanan_maclar = Mac.objects.filter(turnuva=aktif_turnuva, durum='oynandi').order_by('-tarih', '-saat')[:25]

    return render(request, 'core/hakem.html', {'bekleyen_maclar': bekleyen_maclar, 'tamamlanan_maclar': tamamlanan_maclar})


# ==========================================
# GENEL ZİYARETÇİ FİKSTÜR GÖRÜNÜMÜ
# ==========================================
def fikstur(request):
    aktif_turnuva = Turnuva.objects.order_by('-id').first()
    kategoriler = Kategori.objects.all() if aktif_turnuva else []
    eleme_sirasi = ["Son 128", "Son 64", "Son 32", "Son 16", "Çeyrek Final", "Yarı Final", "Final"]
    
    secili_kategori = None
    gruplar_verisi = []
    eleme_maclari = []
    
    kat_id = request.GET.get('kategori')
    if kat_id: secili_kategori = Kategori.objects.filter(id=kat_id).first()
    elif kategoriler: secili_kategori = kategoriler.first()
        
    if secili_kategori and aktif_turnuva:
        grup_isimleri = Mac.objects.filter(
            turnuva=aktif_turnuva, kategori=secili_kategori
        ).exclude(grup__in=eleme_sirasi).exclude(grup='BAY').values_list('grup', flat=True).distinct()
        
        for grup_adi in grup_isimleri:
            istatistikler = puan_durumu_hesapla(grup_adi, secili_kategori, aktif_turnuva)
            grup_maclari = Mac.objects.filter(
                turnuva=aktif_turnuva, kategori=secili_kategori, grup=grup_adi
            ).order_by('tarih', 'saat')
            
            gruplar_verisi.append({
                'grup_ismi': grup_adi,
                'oyuncular': istatistikler,
                'maclar': grup_maclari
            })
            
        eleme_maclari = Mac.objects.filter(
            turnuva=aktif_turnuva, kategori=secili_kategori, grup__in=eleme_sirasi
        ).order_by('id')
            
    return render(request, 'core/fikstur.html', {
        'aktif_turnuva': aktif_turnuva,
        'kategoriler': kategoriler,
        'secili_kategori': secili_kategori,
        'gruplar_verisi': gruplar_verisi,
        'eleme_maclari': eleme_maclari
    })


# ==========================================
# OYUNCU PROFİLİ VE DİĞERLERİ
# ==========================================
@login_required(login_url='/giris/')
def profil(request):
    telefon = request.user.username.strip()
    oyuncu = Kayit.objects.filter(telefon=telefon).first()
    if not oyuncu:
        oyuncu = Kayit.objects.filter(ad__iexact=request.user.first_name, soyad__iexact=request.user.last_name).order_by('-id').first()
    
    if not oyuncu:
        return render(request, 'core/oyuncu_paneli.html', {'mesaj': 'Henüz bir turnuvaya kayıtlı değilsiniz.'})

    oyuncu_maclari = Mac.objects.filter(Q(oyuncu1=oyuncu) | Q(oyuncu2=oyuncu))
    
    if oyuncu.turnuva and not oyuncu.turnuva.eleme_yayinlandi:
        eleme_sirasi = ["Son 128", "Son 64", "Son 32", "Son 16", "Çeyrek Final", "Yarı Final", "Final"]
        oyuncu_maclari = oyuncu_maclari.exclude(grup__in=eleme_sirasi)
        
    bekleyen_maclar = oyuncu_maclari.filter(durum__in=['planlaniyor', 'bekliyor']).order_by('tarih', 'saat')
    gecmis_maclar = oyuncu_maclari.filter(durum='oynandi').order_by('-tarih', '-saat')
    
    tum_gruplar_verisi = []
    if oyuncu.kategori and oyuncu.turnuva:
        grup_isimleri = Kayit.objects.filter(
            turnuva=oyuncu.turnuva, kategori=oyuncu.kategori
        ).exclude(grup__isnull=True).exclude(grup='').exclude(grup='BAY').values_list('grup', flat=True).distinct()
        
        for grup_adi in grup_isimleri:
            istatistikler = puan_durumu_hesapla(grup_adi, oyuncu.kategori, oyuncu.turnuva)
            grup_maclari = Mac.objects.filter(turnuva=oyuncu.turnuva, kategori=oyuncu.kategori, grup=grup_adi).order_by('tarih', 'saat')
            tum_gruplar_verisi.append({
                'grup': {'isim': grup_adi}, 'istatistikler': istatistikler, 'maclar': grup_maclari, 'is_kendi_grubu': (grup_adi == oyuncu.grup)
            })
        tum_gruplar_verisi.sort(key=lambda x: (not x['is_kendi_grubu'], x['grup']['isim']))

    return render(request, 'core/oyuncu_paneli.html', {
        'oyuncu': oyuncu, 'kategori': oyuncu.kategori,
        'oyuncunun_grubu': {'isim': oyuncu.grup} if oyuncu.grup else None,
        'bekleyen_maclar': bekleyen_maclar, 'gecmis_maclar': gecmis_maclar,
        'tum_gruplar_verisi': tum_gruplar_verisi
    })


@login_required(login_url='/giris/')
def rezervasyon_paneli(request):
    if not request.user.is_staff: return redirect('index')
    tarih_str = request.GET.get('tarih')
    secili_tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date() if tarih_str else timezone.now().date()

    if request.method == 'POST':
        kort_no, saat, kisi_adi, aciklama = request.POST.get('kort'), request.POST.get('saat'), request.POST.get('kisi_adi'), request.POST.get('aciklama')
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

        basarili = 0
        for hafta in range(tekrar_hafta):
            hedef_tarih = secili_tarih + timedelta(days=7 * hafta)
            hedef_gun_kapali = KapaliDurum.objects.filter(tarih=hedef_tarih)
            if hedef_gun_kapali.filter(kort='Hepsi').exists() or hedef_gun_kapali.filter(kort=kort_no).exists(): continue 
            if not Rezervasyon.objects.filter(kort=kort_no, tarih=hedef_tarih, saat=saat).exists():
                Rezervasyon.objects.create(kort=kort_no, tarih=hedef_tarih, saat=saat, rezerve_eden=kayit_sahibi, kisi_adi=kisi_adi, aciklama=aciklama)
                basarili += 1

        if basarili > 0: messages.success(request, "Rezervasyon eklendi.")
        else: messages.error(request, "Seçilen saatler dolu.")
        return redirect(f'/rezervasyon/?tarih={secili_tarih.strftime("%Y-%m-%d")}')

    gunun_rezervasyonlari = Rezervasyon.objects.filter(tarih=secili_tarih)
    rez_dict = {(r.kort, r.saat): r for r in gunun_rezervasyonlari}
    kapali_durumlar = KapaliDurum.objects.filter(tarih=secili_tarih)
    kapali_kortlar = {k.kort: k.sebep for k in kapali_durumlar}
    genel_kapanis = kapali_kortlar.get('Hepsi') 

    matrix = []
    for saat in [f"{s:02d}:00" for s in range(8, 24)]:
        satir = {'saat': saat, 'kortlar': []}
        for kort in ['1', '2', '3', '4']:
            rez = rez_dict.get((kort, saat))
            sebep = genel_kapanis or kapali_kortlar.get(kort)
            satir['kortlar'].append({
                'kort_no': kort, 'durum': 'kapali' if sebep else ('dolu' if rez else 'bos'),
                'rezervasyon': rez, 'sebep': sebep if sebep else None
            })
        matrix.append(satir)

    return render(request, 'core/rezervasyon.html', {
        'secili_tarih': secili_tarih,
        'onceki_gun': (secili_tarih - timedelta(days=1)).strftime('%Y-%m-%d'),
        'sonraki_gun': (secili_tarih + timedelta(days=1)).strftime('%Y-%m-%d'),
        'matrix': matrix, 'hocalar': User.objects.filter(is_staff=True, is_superuser=False) if request.user.is_superuser else None
    })


@login_required(login_url='/giris/')
def muhasebe_paneli(request):
    if not request.user.is_superuser: return redirect('rezervasyon_paneli')
    tarih_str = request.GET.get('tarih')
    secili_tarih = datetime.strptime(tarih_str, '%Y-%m-%d').date() if tarih_str else timezone.now().date()
    ay_basi = secili_tarih.replace(day=1)
    ay_sonu = secili_tarih.replace(year=secili_tarih.year+1, month=1, day=1) - timedelta(days=1) if secili_tarih.month == 12 else secili_tarih.replace(month=secili_tarih.month+1, day=1) - timedelta(days=1)
    hafta_basi = secili_tarih - timedelta(days=secili_tarih.weekday())
    hafta_sonu = hafta_basi + timedelta(days=6)
    
    rapor = []
    for hoca in User.objects.filter(is_staff=True, is_superuser=False):
        hoca_dersleri = Rezervasyon.objects.filter(rezerve_eden=hoca, tarih__range=[ay_basi, ay_sonu])
        rapor.append({
            'isim': hoca.first_name if hoca.first_name else hoca.username,
            'bugun': hoca_dersleri.filter(tarih=secili_tarih).count(),
            'bu_hafta': hoca_dersleri.filter(tarih__range=[hafta_basi, hafta_sonu]).count(),
            'bu_ay': hoca_dersleri.count(), 'ders_listesi': hoca_dersleri.order_by('-tarih', '-saat')
        })

    return render(request, 'core/muhasebe.html', {
        'rapor': rapor, 'secili_tarih': secili_tarih,
        'onceki_hafta': (secili_tarih - timedelta(days=7)).strftime('%Y-%m-%d'),
        'sonraki_hafta': (secili_tarih + timedelta(days=7)).strftime('%Y-%m-%d'),
        'ay_ismi': turkce_tarih_format(secili_tarih).split(' ')[1] + " " + str(secili_tarih.year) + " Özeti",
        'hafta_bilgi': f"{turkce_tarih_format(hafta_basi)} - {turkce_tarih_format(hafta_sonu)} Haftası"
    })


@login_required(login_url='/giris/')
def rezervasyon_sil(request, rez_id):
    if not request.user.is_superuser: return redirect('rezervasyon_paneli')
    rez = get_object_or_404(Rezervasyon, id=rez_id)
    donulecek_tarih = rez.tarih.strftime('%Y-%m-%d')
    rez.delete()
    messages.success(request, "Rezervasyon iptal edildi.")
    return redirect(f'/rezervasyon/?tarih={donulecek_tarih}')


def manifest_view(request):
    return JsonResponse({
        "id": "at-rezervasyon-v2", "name": "AT Rezervasyon", "short_name": "Rezervasyon",
        "start_url": "/rezervasyon/", "scope": "/rezervasyon/", "display": "standalone",
        "background_color": "#f4f6f9", "theme_color": "#0a2342",
        "icons": [{"src": "https://i.ibb.co/HTPhptVQ/logo.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"}]
    })


def cikis_yap(request):
    logout(request)
    messages.info(request, "Çıkış yapıldı.")
    return redirect('giris')


@login_required(login_url='/giris/')
def sifre_degistir(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Şifreniz güncellendi!')
            return redirect('rezervasyon_paneli')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'core/sifre_degistir.html', {'form': form})