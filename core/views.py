from django.shortcuts import render

def index(request):
    # Turnuva verilerini kaldırdık, sadece sayfayı gösteriyoruz.
    return render(request, 'core/index.html')