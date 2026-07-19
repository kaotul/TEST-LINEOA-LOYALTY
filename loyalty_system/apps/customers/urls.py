from django.urls import path
from . import views

app_name = "customers"

urlpatterns = [
    path("", views.liff_index, name="liff_index"),
    path("history/", views.liff_history, name="liff_history"),
    path("api/login/", views.liff_login, name="liff_login"),
    path("api/qrcode/", views.liff_qrcode, name="liff_qrcode"),
]
