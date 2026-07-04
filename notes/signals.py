from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Participant


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_participant(sender, instance, created, **kwargs):
    if created:
        Participant.objects.get_or_create(user=instance)
