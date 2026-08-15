"""
Django 6.0 settings — Loyalty Program (LINE OA)
Python 3.12+ required.
"""
import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-secret-change-me")
DEBUG = env.bool("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_celery_beat",
    "customers",
    "points",
    "pos",
    "line_integration",
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
    # Django 6.0 native CSP — ปรับ policy ให้ตรงกับโดเมน LIFF ของจริงก่อนใช้งานจริง
    #"django.middleware.csp.ContentSecurityPolicyMiddleware",
]

SECURE_CSP = {
    "DIRECTIVES": {
        "default-src": ["'self'"],
        "img-src": ["'self'", "data:", "https://*.line-scdn.net"],
        "script-src": ["'self'", "https://static.line-scdn.net"],
        "connect-src": ["'self'", "https://api.line.me"],
        "frame-ancestors": ["https://liff.line.me"],
    }
}

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# DATABASES = {
#     "default": env.db("DATABASE_URL", default="postgres://loyalty:loyalty@localhost:5432/loyalty_db")
# }
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
DATABASES["default"]["CONN_MAX_AGE"] = 60

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "th"
TIME_ZONE = "Asia/Bangkok"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"  # เก็บไฟล์ QR Code ของลูกค้า

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
}

# ---------------- Celery (จัดการงานหมดอายุแต้ม + แจ้งเตือนรายวัน) ----------------
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/0")
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TIMEZONE = TIME_ZONE

# ---------------- LINE Official Account ----------------
LINE_CHANNEL_ACCESS_TOKEN = env("LINE_CHANNEL_ACCESS_TOKEN", default="")
LINE_CHANNEL_SECRET = env("LINE_CHANNEL_SECRET", default="")
LIFF_ID = env("LIFF_ID", default="")            # LIFF app แสดงหน้าคะแนน
LIFF_CHANNEL_ID = env("LIFF_CHANNEL_ID", default="")  # LINE Login channel id ของ LIFF app (ใช้ verify id_token)
LIFF_BASE_URL = env("LIFF_BASE_URL", default="https://liff.line.me")

# ---------------- ธุรกิจ: กติกาสะสมแต้ม ----------------
BAHT_PER_POINT = env.int("BAHT_PER_POINT", default=50)   # ทุก 50 บาท = 1 แต้ม
POINT_EXPIRY_DAYS = env.int("POINT_EXPIRY_DAYS", default=365)  # แต้มหมดอายุใน 1 ปี
EXPIRY_WARNING_DAYS = env.int("EXPIRY_WARNING_DAYS", default=30)  # เตือนล่วงหน้า 30 วันก่อนหมดอายุ


#----------------------------------------------------------------------------------------
# LOGGER
#----------------------------------------------------------------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            'format': u'%(name)-12s %(levelname)-8s %(message)s'
        },        
        'verbose': {
            'format': u'{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': u'{levelname} {message}',
            'style': '{',
        },
        'prod_format': {
            'format': '[{asctime}] [{levelname}] [{name}:{lineno}] {message}',
            'style': '{',
        },                  
    },
    'filters': {
        'special': {
            #'()': 'project.logging.SpecialFilter',
            'foo': 'bar',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'file': {
            #'level': 'DEBUG',
            #'class': 'logging.FileHandler',
            #'filename': f'{BASE_DIR}/debug.log',
            #'formatter': 'verbose',
            #'encoding': 'UTF-8',
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': os.path.join(BASE_DIR, '', 'debug.log'),
            'when': 'midnight',  # Rotate at midnight
            'interval': 1,       # Every day
            'backupCount': 7,    # Keep 7 days of logs
            'formatter': 'verbose',          
            'encoding': 'UTF-8',            
        },        
        'console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler',
            'filters': ['special'],   
        },
    },
    'loggers': {
        'CORE': {
            'handlers': ['console',],
            'level': os.environ.get("DJANGO_LOG_LEVEL", "DEBUG"),
            'propagate': True,
        },
    }
}