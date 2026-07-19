from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="pos-dashboard"),
    path("api/lookup/", views.lookup_customer, name="pos-lookup"),
    path("api/award/", views.award, name="pos-award"),
]
