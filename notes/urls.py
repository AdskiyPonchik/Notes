from django.contrib import admin
from django.views.generic import TemplateView
from django.contrib.auth.views import LogoutView
from django.urls import path
from .views import NoteListView, Login, logout_view, Signup, EmailVerify

urlpatterns = [
    path('', NoteListView.as_view(), name='home'),
    path('login/', Login.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('signup/', Signup.as_view(), name='signup'),
    path('confirm_email', TemplateView.as_view(template_name='notes/confirm_email.html'),
         name='confirm_email'),
    path('verify_email/<uidb64>/<token>/', EmailVerify.as_view(), name='verify_email'),
    path('invalid_token/', TemplateView.as_view(template_name='registration/invalid_token.html'),
         name='invalid_token')
]
