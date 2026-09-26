from django.contrib import admin
from .models import Party, Candidate
from unfold.admin import ModelAdmin
# Register your models here.

my_models = [Party, Candidate]

for model in my_models:
    admin.site.register(model, ModelAdmin)