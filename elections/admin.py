from django.contrib import admin
from .models import Election, Position
from unfold.admin import ModelAdmin
# Register your models here.

my_models = [Election, Position]

for model in my_models:
    admin.site.register(model, ModelAdmin)
