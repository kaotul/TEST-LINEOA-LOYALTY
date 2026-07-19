from django.urls import path
from . import views

app_name = "pos"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("scan/", views.scan_page, name="scan"),
    path("scan/lookup/", views.lookup_customer, name="lookup_customer"),
    path("scan/award/", views.award_points_view, name="award_points"),
    path("scan/redeem/", views.redeem_points_view, name="redeem_points"),
    path("settings/", views.settings_view, name="settings"),
    path("reports/", views.reports_view, name="reports"),
]
