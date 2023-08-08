from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.urls import path
from .views import NoteListView, Login
urlpatterns = [
    path('', NoteListView.as_view(), name='home'),
    path('login/', Login.as_view(), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout')
]