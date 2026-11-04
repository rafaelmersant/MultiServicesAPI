"""Isolated DGII receiver deployment; never points at the commercial database."""

import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

# This file is used only by the separate Gunicorn service. Existing settings
# and the commercial application retain their current behavior.
load_dotenv(os.getenv("ECF_ENV_FILE", "/etc/multiservices-certification.env"), override=False)

from .settings import *  # noqa: E402,F401,F403

if os.getenv("DGII_ENVIRONMENT", "").strip().lower() != "cert":
    raise ImproperlyConfigured("El servicio aislado requiere DGII_ENVIRONMENT=cert.")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "")
if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("Configura DJANGO_SECRET_KEY con al menos 50 caracteres aleatorios.")

DEBUG = False
ALLOWED_HOSTS = [h.strip() for h in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if h.strip()]
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("Configura DJANGO_ALLOWED_HOSTS con el dominio de certificación.")

database_path = Path(os.environ.get("ECF_CERTIFICATION_DB", ""))
if not database_path.is_absolute() or database_path.resolve() == Path(BASE_DIR, "db.sqlite3").resolve():
    raise ImproperlyConfigured("ECF_CERTIFICATION_DB debe ser una ruta absoluta a otra base de datos.")
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": str(database_path), "OPTIONS": {"timeout": 30}}}
MEDIA_ROOT = os.getenv("ECF_CERTIFICATION_MEDIA", "/var/lib/multiservices-certification/media")
ROOT_URLCONF = "MultiServices.urls_certification"
TIME_ZONE = "America/Santo_Domingo"
INSTALLED_APPS = [app for app in INSTALLED_APPS if app != "debug_toolbar"]
MIDDLEWARE = [entry for entry in MIDDLEWARE if "debug_toolbar" not in entry]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 3600
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
CORS_ORIGIN_ALLOW_ALL = False
