import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ahalteke.settings')

application = get_wsgi_application()

app = application  # <-- İŞTE BU SATIRI EKLEMEN GEREKİYOR