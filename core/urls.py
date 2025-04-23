from django.urls import path 
from . import views

urlpatterns = [
    path('upload', views.upload, name='upload'),
    path('download/all', views.download, name='download_all'),
    path('territories/', views.territory_list_page, name='territory_list'),
    path('territory/<str:territory_code>/', views.territory_detail, name='territory_detail'),
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/logout/', views.user_logout, name='logout'),
    path('',views.home, name='home'),
]