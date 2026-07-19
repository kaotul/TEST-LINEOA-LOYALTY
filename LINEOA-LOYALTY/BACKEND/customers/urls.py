from django.urls import path

from . import views

urlpatterns = [
    path("api/liff/register/", views.register_or_login, name="liff-register"),
    path("api/liff/me/", views.my_points_summary, name="liff-me"),
    path("qr/<uuid:qr_token>.png", views.customer_qr_image, name="customer-qr-image"),
]
