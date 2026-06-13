"""
Django settings for ahalteke project.
"""

from pathlib import Path
import os
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-change-me-later-for-production-security'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# Vercel'de çalışması için tüm hostlara izin veriyoruz
ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Kendi uygulamamız:
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise Middleware'i BURADA olmalı (Security'den hemen sonra):
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'ahalteke.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'ahalteke.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

# --- KRİTİK DÜZELTME BURADA ---
# Eğer sistemde DATABASE_URL varsa (yani Vercel/Canlı Sunucudaysa) Neon/Vercel veritabanını kullan
if 'DATABASE_URL' in os.environ:
    DATABASES = {
        'default': dj_database_url.config(conn_max_age=600)
    }
# Eğer yoksa (yani senin bilgisayarındaysa) yerel SQLite veritabanını kullan
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'tr-tr'

TIME_ZONE = 'Europe/Istanbul'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'

# Vercel'in dosyaları toplayacağı yer (Root)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# WhiteNoise Sıkıştırma Ayarı (Vercel'de resimlerin görünmesi için KRİTİK)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Django'nun statik dosyaları (logo vb.) nerede arayacağı
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "core/static"),
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CSRF_TRUSTED_ORIGINS = [
    'https://*.vercel.app',  # Vercel'in oluşturduğu tüm linklere izin verir
    'https://www.ahalteketeniskulubu.com', # Varsa kendi domainini ekle
    'https://ahalteketeniskulubu.com',
]

CSRF_COOKIE_SECURE = True
SESSION_COOKIE_SECURE = True

# ==========================================
# E-POSTA GÖNDERME AYARLARI (SMTP)
# ==========================================
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'ahalteke2026@gmail.com' 
EMAIL_HOST_PASSWORD = 'jiwt kfkf rlae isaz'
DEFAULT_FROM_EMAIL = 'Ahal Teke Tenis Kulübü <ahalteke2026@gmail.com>'

# Giriş yapıldığında nereye gitsin (Fikstür kapalı olduğu için Profil'e gidiyor)
LOGIN_REDIRECT_URL = 'profil'
LOGOUT_REDIRECT_URL = 'index'