from django.dispatch import receiver
from django.db.models.signals import post_save
from accounts.models import Profile, User
from django.conf import settings
import string
import secrets

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)