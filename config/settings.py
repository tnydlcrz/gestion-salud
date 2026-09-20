from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, True),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="dev-only-cambiar-antes-de-produccion")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

for extra in (
    env("RENDER_EXTERNAL_HOSTNAME", default=""),
    env("KOYEB_PUBLIC_DOMAIN", default=""),
):
    if extra and extra not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(extra)

if not DEBUG:
    if SECRET_KEY == "dev-only-cambiar-antes-de-produccion":
        raise ImproperlyConfigured("SECRET_KEY debe definirse en el entorno de producción.")
    for wildcard in (".onrender.com", ".koyeb.app"):
        if wildcard not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(wildcard)

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
if not DEBUG:
    for origin in ("https://*.onrender.com", "https://*.koyeb.app"):
        if origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(origin)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "cuentas",
    "indicadores",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "cuentas.context_processors.areas_nav",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://tablero:tablero@127.0.0.1:5432/tablero",
    )
}
if DATABASES["default"].get("ENGINE", "").endswith("postgresql"):
    DATABASES["default"].setdefault("OPTIONS", {})
    host = DATABASES["default"].get("HOST") or ""
    DATABASES["default"]["OPTIONS"].pop("channel_binding", None)
    DATABASES["default"]["OPTIONS"].setdefault("connect_timeout", 5)
    if "neon.tech" in host:
        # El pooler de Neon no debe reutilizar conexiones de Django:
        # CONN_MAX_AGE > 0 deja sockets muertos y cada clic espera el timeout.
        DATABASES["default"]["OPTIONS"]["sslmode"] = "require"
        DATABASES["default"]["CONN_MAX_AGE"] = 0
        DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
    elif not DEBUG:
        DATABASES["default"]["OPTIONS"]["sslmode"] = "require"
        DATABASES["default"]["CONN_MAX_AGE"] = 60
        DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
    else:
        DATABASES["default"]["OPTIONS"].setdefault("sslmode", "prefer")

AUTH_USER_MODEL = "cuentas.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
]

LANGUAGE_CODE = "es-ar"
TIME_ZONE = "America/Argentina/Buenos_Aires"
USE_I18N = True
USE_TZ = True
DEFAULT_CHARSET = "utf-8"

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "tablero:home"
LOGOUT_REDIRECT_URL = "login"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
