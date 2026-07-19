from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("pos/", include("apps.pos.urls")),
    path("liff/", include("apps.customers.urls")),
    path("line/", include("apps.lineoa.urls")),
    path("api/", include("apps.loyalty.urls")),
    path("", include("apps.pos.urls_root")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
