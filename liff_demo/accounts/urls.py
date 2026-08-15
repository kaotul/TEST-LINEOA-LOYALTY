from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.liff_login_page, name='liff_login_page'),
    path('verify/', views.liff_verify, name='liff_verify'),
    path('profile/', views.profile, name='profile'),
    path('logout/', views.liff_logout, name='liff_logout'),
]
