from django import forms
from .models import Kayit

class KayitForm(forms.ModelForm):
    class Meta:
        model = Kayit
        # partner_adi listeden çıkarıldı
        fields = ['kategori', 'ad', 'soyad', 'telefon']
        
        widgets = {
            'kategori': forms.Select(attrs={'class': 'form-select'}),
            'ad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Adınız'}),
            'soyad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Soyadınız'}),
            'telefon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '05XX XXX XX XX'}),
        }