from django.db import models
from elections.models import Election, Position
from parties.models import Party, Candidate
from django.contrib.auth import get_user_model
from django.conf import settings

import secrets
import string
# Create your models here.

User = get_user_model()

class State(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self) -> str:
        return self.name
    
class LGA(models.Model):
    class Meta:
        verbose_name = "Local Government Area"
        verbose_name_plural = "Local Government Areas"
        constraints = [
            models.UniqueConstraint(
                fields=['state', 'name'],
                name='unique_lga_per_state',
            )
        ]
        
    name = models.CharField(max_length=100)
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name='lgas')
    
    def __str__(self):
        return f"{self.name}, {self.state.name}"
    
class Ward(models.Model):
    
    class Meta:
        verbose_name = "Ward"
        verbose_name_plural = "Wards"
        constraints = [
            models.UniqueConstraint(
                fields=['lga', 'name'],
                name='unique_ward_per_lga',
            )
        ]
    
    name = models.CharField(max_length=100)
    lga = models.ForeignKey(LGA, on_delete=models.CASCADE, related_name='wards')
    
    def __str__(self) -> str:
        return f"{self.name}, {self.lga.name}, {self.lga.state.name}"
    
    
class PollingUnit(models.Model):
    class Meta:
        verbose_name = "Polling Unit"
        verbose_name_plural = "Polling Units"
        constraints = [
            models.UniqueConstraint(
                fields=['ward', 'name'],
                name='unique_polling_unit_per_ward',
            )
        ]
    name = models.CharField(max_length=255)
    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='polling_units')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True,)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True,)
    
    def __str__(self) -> str:
        return f"{self.name}, {self.ward.name} {self.ward.lga.name}, {self.ward.lga.state.name}"

class Vote(models.Model):
    voter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ballots')
    election = models.ForeignKey(Election, on_delete=models.CASCADE, related_name='votes')
    position = models.ForeignKey(Position, on_delete=models.CASCADE, related_name='votes')
    candidate = models.ForeignKey(Candidate, on_delete=models.PROTECT, related_name='ballots')
    voted_at = models.DateTimeField(auto_now_add=True)
    
class Voter(models.Model):
    class Status(models.TextChoices):
        NOT_APPLIED = 'not_applied', 'Not Applied'
        PENDING = 'pending', 'Pending Approval'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='voter')
    vin = models.CharField(max_length=20, null=True, unique=True, blank=True)
    polling_unit = models.ForeignKey(PollingUnit, on_delete=models.PROTECT)
    voter_status = models.CharField(max_length=50, choices=Status.choices, default=Status.NOT_APPLIED)
    passport = models.ImageField(upload_to="passports/")
    registration_date = models.DateField(auto_now_add=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_voters')
    approved_at =models.DateTimeField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f"{self.user.get_user_full_name()} - {self.voter_status}"
    
    def save(self, *args, **kwargs):
        random_numbers = "".join(secrets.choice(string.digits) for _ in range(7))
        secure_vin = f"VIN-{random_numbers}"
        
        if not self.vin:
            self.vin = secure_vin
        return super().save(*args, **kwargs)