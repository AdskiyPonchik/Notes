from django.contrib import admin
from .models import Note, Participant


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ['user', 'email', 'profileimg', 'email_token', 'email_verified']
    list_filter = ['email', 'email_verified']
    search_fields = ['user', 'email']


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ['title', 'text', 'created_at', 'participant', 'status']
    list_filter = ['created_at']
    search_fields = ['title', 'text', 'participant']
    raw_id_fields = ['participant']
    date_hierarchy = 'created_at'
    ordering = ['status']
