from .models import Participant


def mark_email_verified(backend, user, **kwargs):
    """Google verifies email ownership itself, so OAuth users skip our email check."""
    if backend.name == 'google-oauth2':
        Participant.objects.update_or_create(
            user=user, defaults={'email_verified': True}
        )
