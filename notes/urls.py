from django.views.generic import TemplateView
from django.urls import path, include
from .views import (NoteListView, Login, logout_view, Signup, EmailVerify,
                    get_notes, update_note, note_action)

urlpatterns = [
    path('', NoteListView.as_view(), name='home'),
    path('get_notes/', get_notes, name='get_notes'),
    path('notes/update/<int:note_id>/', update_note, name='update_note'),
    path('notes/<int:note_id>/<str:action>/', note_action, name='note_action'),
    path('login/', Login.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
    path('signup/', Signup.as_view(), name='signup'),
    path('confirm_email/', TemplateView.as_view(template_name='notes/confirm_email.html'),
         name='confirm_email'),
    path('verify_email/<uidb64>/<token>/', EmailVerify.as_view(), name='verify_email'),
    path('invalid_token/', TemplateView.as_view(template_name='notes/invalid_token.html'),
         name='invalid_token'),
    path('social_auth/', include('social_django.urls', namespace='social')),
]