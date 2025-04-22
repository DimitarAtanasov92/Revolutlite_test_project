from django.urls import path
from . import views
from .views import verification_view

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('verify/', verification_view, name='verify')
]
