from django.urls import path
from . import views
# from .views import verification_view # Already imported via views.*

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('', views.login_view, name='login'), # Login at root
    path('login/', views.login_view, name='login'), # Explicit login path
    path('logout/', views.logout_view, name='logout'),
    path('verify/', views.verification_view, name='verify') # Use verification_view
]
