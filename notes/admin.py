from django.contrib import admin
from .models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ['title', 'text', 'created_at', 'participant', 'status']
    list_filter = ['created_at']
    search_fields = ['title', 'text', 'participant']
    raw_id_fields = ['participant']
    date_hierarchy = 'created_at'
    ordering = ['status']
