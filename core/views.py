from django.shortcuts import render

# Ana Sayfa
def index(request):
    return render(request, 'core/index.html')

# Yeni Turnuvalar Sayfası
def turnuvalar(request):
    return render(request, 'core/turnuvalar.html')