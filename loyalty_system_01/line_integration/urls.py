from django.urls import path

from . import views
from .webhook import line_webhook

urlpatterns = [
    path("webhook/", line_webhook, name="line-webhook"),
    path("liff/points/", views.liff_points_page, name="liff-points-page"),
]
