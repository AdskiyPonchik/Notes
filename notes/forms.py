from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Note
from .utils import send_email_for_verify

User = get_user_model()


class LoginForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        participant = getattr(user, 'participant', None)
        if participant and not participant.email_verified:
            send_email_for_verify(self.request, user)
            raise ValidationError(
                _('Email not verified — a new confirmation link was sent to your inbox.'),
                code='unverified',
            )


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'})
    )

    class Meta:
        model = User
        fields = ('username', 'email')

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError(
                _('An account with this email already exists.'),
                code='duplicate_email',
            )
        return email


class NoteAppend(forms.ModelForm):
    class Meta:
        model = Note
        fields = ['title', 'text']
