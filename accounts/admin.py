from django.contrib import admin
from .models import User, Profile
from unfold.admin import ModelAdmin
# Register your models here.

my_models = [User, Profile]

for model in my_models:
    admin.site.register(model, ModelAdmin)