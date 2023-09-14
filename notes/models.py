from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

# Create your models here.
class Participant(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    email = models.EmailField(max_length=255, verbose_name='email')
    profileimg = models.ImageField(upload_to='profile_images', default='default.png')
    email_token = models.CharField(max_length=200)
    email_verified = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username


class Note(models.Model):
    class Status(models.TextChoices):
        ALL = 'A', 'All'
        FAVORITE = 'F', 'Favorite'

    title = models.CharField(max_length=255)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    participant = models.ForeignKey(Participant, related_name='notes', on_delete=models.CASCADE)
    status = models.CharField(max_length=2, choices=Status.choices, default=Status.ALL)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['created_at'])
        ]

    def __str__(self):
        return self.title
