from django.contrib import admin
from .models import Vote, State, LGA, Ward, PollingUnit, Voter
from unfold.admin import ModelAdmin

# Register your models here.
my_models = [State, LGA, Ward, PollingUnit, Voter, Vote]

for model in my_models:
    admin.site.register(model, ModelAdmin)
