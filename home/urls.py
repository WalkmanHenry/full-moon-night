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

    # Manage Cards
    path('cards', views.cards_index, name='cards_index'),
    path('cards/list', views.cards_list, name='cards_list'),

    # Manage Formation
    path('formation', views.formation_index, name='formation_index'),
    path('formation/save', views.formation_save, name='formation_save'),
    path('formation/list', views.formation_list, name='formation_list'),
    path('formation/remove', views.formation_remove, name='formation_remove'),
]
