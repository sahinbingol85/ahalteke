from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    priority = 0.9 # Ana sayfaların önemi (0.0 ile 1.0 arası)
    changefreq = 'weekly' # Ne sıklıkla güncelleniyor

    def items(self):
        # urls.py içindeki path name'leri buraya yazıyoruz
        return ['index', 'turnuvalar', 'fikstur']

    def location(self, item):
        return reverse(item)