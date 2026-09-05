from .models import Turnuva

def turnuva_durumu(request):
    # Henüz tamamlanmamış (aktif/devam eden) turnuva var mı?
    aktif_turnuva_var_mi = Turnuva.objects.filter(tamamlandi=False).exists()
    return {
        'aktif_turnuva_var_mi': aktif_turnuva_var_mi
    }