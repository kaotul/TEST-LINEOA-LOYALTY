from django.urls import path

from .views import MemberCardView, MemberRegisterView, MemberStatusView

urlpatterns = [
    path("status/", MemberStatusView.as_view(), name="member-status"),
    path("register/", MemberRegisterView.as_view(), name="member-register"),
    path("card/", MemberCardView.as_view(), name="member-card"),
]
