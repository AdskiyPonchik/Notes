from django.db import models
from django.conf import settings
from django.contrib.auth.models import User


# Create your models here.
class Participant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    profileimg = models.ImageField(upload_to='profile_images', default='default.png')

    def __str__(self):
        return self.user.username

class Note(models.Model):
    class Status(models.TextChoices):
        COMMON = 'C', 'Common'
        FAVORITE = 'F', 'Favorite'

    title = models.CharField(max_length=255)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    participant = models.ForeignKey(Participant, related_name='notes', on_delete=models.CASCADE)
    status = models.CharField(max_length=2, choices=Status.choices, default=Status.COMMON)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['created_at'])
        ]

    def __str__(self):
        return self.title


