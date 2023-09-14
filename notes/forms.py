from django import forms
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import Participant
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .utils import send_email_for_verify

User = get_user_model()

class LoginForm(AuthenticationForm):
    def clean(self):
        username = forms.CharField(max_length=255)
        password = forms.CharField(widget=forms.PasswordInput)

        if username is not None and password:
            self.user_cache = authenticate(self.request,
                                           username=username,
                                           password=password)
            if not self.user_cache.email_verify:
                send_email_for_verify(self.request, self.user_cache)
                raise ValidationError(
                    'Email not verified, check your email',
                    code='invalid login'
                )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            else:
                self.confirm_login_allowed()
        return self.data


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'})
    )
    class Meta:
        model = User
        fields = ('username', 'email')

    def clean_password2(self):
        cd = self.cleaned_data
        if cd['password1'] != cd['password2']:
            raise forms.ValidationError("Passwords don't match")
        return cd["password2"]
