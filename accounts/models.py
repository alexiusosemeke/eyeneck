from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):
    
    class RoleChoices(models.TextChoices): 
        USER = 'user', 'User'
        ELECTORAL_OFFICER = 'electoral_officer', 'Electoral Officer'
        CANDIDATE = 'candidate', 'Candidate'
        ADMIN = 'admin', 'Admin'
        
    middle_name = models.CharField(max_length=50, blank=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=50, choices=RoleChoices.choices, default=RoleChoices.USER)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def get_user_full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
    
    def __str__(self) -> str:
        full_name = self.get_user_full_name().strip()
        return full_name if full_name else self.email

    def save(self, *args, **kwargs):
        if self.username:
            self.username = self.username.strip().lower()

        super().save(*args, **kwargs)

class Gender(models.TextChoices):
    MALE = "male", "Male"
    FEMALE = "female", "Female"
    OTHER = "other", "Other"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    telephone_number = models.CharField(max_length=20, blank=True, null=True)
    gender = models.CharField(max_length=20, choices=Gender.choices, default=Gender.MALE)
    date_of_birth = models.DateField(blank=True, null=True)
    state_of_origin = models.CharField(max_length=100, null=True, blank=True)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    
    def __str__(self) -> str:
        return f"{self.user.get_user_full_name()}'s profile"
    
    
class ActivityLog(models.Model):
    
    class Action(models.TextChoices):
        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"
        REGISTER_VOTER = "register_voter", "Registered as Voter"
        VOTE = "vote", "Cast Vote"
        UPDATE_PROFILE = "update_profile", "Updated Profile"
        CHANGE_PASSWORD = "change_password", "Changed Password"
    
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        PROCESSING = "processing", "Processing"
        SUCESS = "success", "Success"
        FAILED = "failed", "Failed"
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activity_logs")
    action = models.CharField(max_length=50, choices=Action.choices)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices)
    created_at = models.DateField(auto_now_add=True)
    
    class Meta:
        ordering = ["-created_at"]
    
    def __str__(self) -> str:
        return f"{self.user.get_user_full_name()}'s activity."
    
