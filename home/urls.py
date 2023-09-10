from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),

    # Manage images that need to be imported
    path('imgmanagement', views.imgmanagement_index, name='imgmanagement_index'),
]
