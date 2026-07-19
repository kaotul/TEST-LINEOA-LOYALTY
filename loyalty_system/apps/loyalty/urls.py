from django.urls import path
from . import views

app_name = "loyalty"

urlpatterns = [
    path("me/summary/", views.my_summary, name="my_summary"),
    path("me/history/", views.my_history, name="my_history"),
]
