from django.urls import path 
from . import views

urlpatterns = [
    path('upload', views.upload, name='upload'),
    path('download/all', views.download, name='download_all'),
]