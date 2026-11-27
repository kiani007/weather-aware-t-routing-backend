from .base import *  # noqa: F401,F403
from .base import env

DATABASES = {"default": env.db("DATABASE_URL", default="sqlite://:memory:")}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
for _logger in ("apps", "django"):
    LOGGING["loggers"][_logger]["level"] = "CRITICAL"  # noqa: F405
