import json
import re

from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.db.models import Count
from django.http import JsonResponse, HttpResponseBadRequest, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.http import urlsafe_base64_decode
from django.views.generic import View

from .forms import LoginForm, RegistrationForm, NoteAppend
from .models import Note
from .utils import send_email_for_verify

User = get_user_model()

TAG_RE = re.compile(r'(?<!\w)#([\w-]+)')

# Which statuses each sidebar view shows. Favorites are active notes,
# so the 'active' view matches both plain and starred notes.
NOTE_FILTERS = {
    'active': (Note.Status.ACTIVE, Note.Status.FAVORITE),
    'archived': (Note.Status.ARCHIVED,),
    'trash': (Note.Status.TRASH,),
}

NOTE_ACTIONS = {
    'archive': Note.Status.ARCHIVED,
    'trash': Note.Status.TRASH,
    'restore': Note.Status.ACTIVE,
}


def extract_tags(text):
    tags = []
    for tag in TAG_RE.findall(text):
        tag = tag.lower()
        if tag not in tags:
            tags.append(tag)
    return tags


def serialize_note(note):
    return {
        'id': note.id,
        'title': note.title,
        'text': note.text,
        'status': note.status,
        'tags': extract_tags(note.text),
    }


@login_required
def get_notes(request):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if not is_ajax:
        return HttpResponseBadRequest('Invalid request')
    if request.method != "GET":
        return JsonResponse({'status': 'Invalid request'}, status=400)

    filter_name = request.GET.get('filter', 'active')
    if filter_name not in NOTE_FILTERS:
        return JsonResponse({'status': 'error', 'errors': 'Unknown filter.'}, status=400)

    queryset = Note.objects.filter(participant__user=request.user)
    notes = [serialize_note(n) for n in queryset.filter(status__in=NOTE_FILTERS[filter_name])]

    tag_param = request.GET.get('tag', '').strip().lstrip('#').lower()
    if tag_param:
        notes = [n for n in notes if tag_param in n['tags']]

    per_status = dict(queryset.values_list('status').annotate(total=Count('id')))
    counts = {name: sum(per_status.get(status, 0) for status in statuses)
              for name, statuses in NOTE_FILTERS.items()}

    return JsonResponse({'notes': notes, 'counts': counts})


@login_required
def note_action(request, note_id, action):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if not is_ajax or request.method != 'POST':
        return HttpResponseBadRequest('Invalid request')

    target_status = NOTE_ACTIONS.get(action)
    if target_status is None:
        raise Http404

    note = get_object_or_404(Note, pk=note_id, participant__user=request.user)
    note.status = target_status
    note.save(update_fields=['status'])
    return JsonResponse({'status': 'success',
                         'note': {'id': note.id, 'status': note.status}})


@login_required
def update_note(request, note_id):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if not is_ajax or request.method != 'POST':
        return HttpResponseBadRequest('Invalid request')

    # Tenant check: looking the note up through the requesting participant
    # makes other users' notes indistinguishable from missing ones (404).
    note = get_object_or_404(Note, pk=note_id, participant=request.user.participant)

    if request.content_type == 'application/json':
        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            data = None
        if not isinstance(data, dict):
            return JsonResponse({'status': 'error', 'errors': 'Invalid JSON'}, status=400)
    else:
        data = request.POST

    errors = {}
    updated_fields = []

    if 'title' in data:
        title = str(data['title']).strip()
        if not title:
            errors['title'] = 'Title cannot be empty.'
        elif len(title) > 255:
            errors['title'] = 'Title cannot exceed 255 characters.'
        else:
            note.title = title
            updated_fields.append('title')

    if 'text' in data:
        text = str(data['text']).strip()
        if not text:
            errors['text'] = 'Text cannot be empty.'
        else:
            note.text = text
            updated_fields.append('text')

    if 'status' in data:
        if data['status'] not in Note.Status.values:
            errors['status'] = 'Invalid status.'
        else:
            note.status = data['status']
            updated_fields.append('status')

    if errors:
        return JsonResponse({'status': 'error', 'errors': errors}, status=400)
    if not updated_fields:
        return JsonResponse({'status': 'error', 'errors': 'No fields to update.'}, status=400)

    note.save(update_fields=updated_fields)
    return JsonResponse({'status': 'success', 'note': {
        'id': note.id, 'title': note.title, 'text': note.text, 'status': note.status,
    }})


class NoteListView(LoginRequiredMixin, View):
    form_class = NoteAppend
    template_name = 'notes/home.html'

    def get(self, request):
        participant = request.user.participant
        return render(request, self.template_name, context={
            'form': self.form_class(),
            'participant': participant,
            'notes': participant.notes.all(),
        })

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST)
        if form.is_valid():
            note = form.save(commit=False)
            note.participant = request.user.participant
            note.save()
            return JsonResponse({'status': 'success'})
        return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)


class Login(LoginView):
    template_name = 'notes/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class Signup(View):
    template_name = "notes/register.html"

    def get(self, request):
        return render(request, self.template_name, {'form': RegistrationForm()})

    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_email_for_verify(request, user=user)
            return redirect('confirm_email')
        return render(request, self.template_name, {'form': form})


class EmailVerify(View):

    def get(self, request, uidb64, token):
        user = self.get_user(uidb64=uidb64)

        if user is not None and default_token_generator.check_token(user, token):
            participant = user.participant
            participant.email_verified = True
            participant.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            return redirect('home')
        return redirect('invalid_token')

    @staticmethod
    def get_user(uidb64):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist, ValidationError):
            user = None
        return user


def logout_view(request):
    logout(request)
    return redirect('login')
