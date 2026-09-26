from django.db import models
from datetime import datetime
import random
import string
from elections.models import Election, Position
from django.contrib.auth import get_user_model
# Create your models here.

User = get_user_model()


class Party(models.Model):
    class Meta:
        verbose_name = "Party"
        verbose_name_plural = "Parties"

    name = models.CharField(max_length=50, unique=True)
    party_initials = models.CharField(max_length=5, unique=True)
    party_slogan = models.CharField(max_length=100, blank=True, null=True)
    logo = models.ImageField(upload_to="party_logos/")
    description = models.TextField()
    date_updated = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


def generate_voter_id():
    year = datetime.now().year
    random_part = "".join(random.choices(string.digits, k=6))
    return f"VOT-{year}-{random_part}"


class Candidate(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="candidate")
    party = models.ForeignKey(
        Party, on_delete=models.PROTECT, related_name="candidates"
    )
    election = models.ForeignKey(
        Election, on_delete=models.CASCADE, related_name="candidates"
    )
    candidate_image = models.ImageField(upload_to="candidate_images/")
    position = models.ForeignKey(
        Position, on_delete=models.CASCADE, related_name="candidates"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.user.get_full_name()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "election"], name="unique_user_election_candidate"
            )
        ]
