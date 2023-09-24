from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('hello', views.hello, name='helloworld'),

    # Manage images that need to be imported
    path('imgmanagement', views.imgmanagement_index, name='imgmanagement_index'),
    path('imgmanagement/cornernumbers', views.imgmanagement_cornernumbers, name='imgmanagement_cornernumbers'),
    path('imgmanagement/cutcard', views.imgmanagement_cutcard, name='imgmanagement_cutcard'),
    path('imgmanagement/imageinit', views.imgmanagement_imageinit, name='imgmanagement_imageinit'),
]
