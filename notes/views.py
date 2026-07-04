from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView
from django.core.exceptions import ValidationError
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import render, redirect
from django.utils.http import urlsafe_base64_decode
from django.views.generic import View

from .forms import LoginForm, RegistrationForm, NoteAppend
from .utils import send_email_for_verify

User = get_user_model()


@login_required
def get_notes(request):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    if not is_ajax:
        return HttpResponseBadRequest('Invalid request')
    if request.method != "GET":
        return JsonResponse({'status': 'Invalid request'}, status=400)
    notes = request.user.participant.notes.all()
    data = [{'id': note.id, 'title': note.title, 'text': note.text} for note in notes]
    return JsonResponse(data, safe=False)


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
