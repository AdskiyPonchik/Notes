from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.urls import reverse_lazy
from django.utils.http import urlsafe_base64_decode
from django.views.generic import ListView, View
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from .models import Note, Participant
from .forms import LoginForm, RegistrationForm
from .utils import send_email_for_verify
from django.db import transaction
from django.shortcuts import render, redirect
from django.views import View
from django.contrib.auth import authenticate, login
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages

User = get_user_model()


# Create your views here.
class NoteListView(ListView):
    queryset = Note.objects.all()
    context_object_name = 'notes'
    template_name = 'notes/home.html'


class Login(View):
    template_name = 'notes/login.html'
    form_class = LoginForm

    def get(self, request):
        form = self.form_class()
        message = ''
        return render(request, self.template_name, context={'form': form, 'message': message})

    def post(self, request):
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                return redirect('home')
            else:
                messages.error(request, 'Your account is disabled')
        else:
            messages.error(request, 'Incorrect username or password')

        return render(request, self.template_name)


class Signup(View):
    template_name = "notes/register.html"

    def get(self, request):
        context = {
            'form': RegistrationForm()
        }
        return render(request, self.template_name, context)

    def post(self, request):
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            password = form.clean_password2()
            # Authenticate the user after creation
            user = authenticate(username=username, password=password)
            new_profile = Participant.objects.create(user=user, email=user.email)
            new_profile.save()
            send_email_for_verify(request, user=user)
            return redirect('confirm_email')

        context = {
            'form': form
        }
        return render(request, self.template_name, context)


class EmailVerify(View):

    def get(self, request, uidb64, token):
        user = self.get_user(uidb64=uidb64)

        if user is not None and default_token_generator.check_token(user, token):
            user.email_verify = True
            user.save()
            profile = Participant.objects.get(user=user)
            profile.email_verified = True
            profile.save()
            login(request, user)
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


"""def user_login(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            user = authenticate(request,
                                username=cd['username'],
                                password=cd['password'])

            if user is not None:
                if user.is_active:
                    login(request, user)
                    return HttpResponse('Authenticated successfully')
                else:
                    return HttpResponse('Disabled account')
            else:
                return HttpResponse('Invalid login')
    else:
        form = LoginForm()
    return render(request, 'notes/login.html', {'form': form})"""
