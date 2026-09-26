from django.db import models

# Create your models here.


class ElectionChoices(models.TextChoices):
    PRIMARY = "primary", "Primary"
    GENERAL = "general", "General"
    RUN_OFF = "run-off", "Run-Off"
    SUPPLEMENTARY = "supplementary", "Supplementary"
    RE_RUN = "re-run", "Re-Run"


class StatusChoices(models.TextChoices):
    DRAFT = "draft", "Draft"
    SCHEDULED = "scheduled", "Scheduled"
    ACTIVE = "active", "Active"
    CLOSED = "closed", "Closed"
    CANCELLED = "cancelled", "Cancelled"


class Election(models.Model):
    title = models.CharField(max_length=220)
    description = models.TextField()
    election_type = models.CharField(
        max_length=50, choices=ElectionChoices.choices, default=ElectionChoices.GENERAL
    )
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(
        max_length=50, choices=StatusChoices.choices, default=StatusChoices.DRAFT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


class PositionChoices(models.TextChoices):
    PRESIDENT = "president", "President"
    GOVERNOR = "governor", "Governor"
    SENATE_PRESIDENT = "senate president", "Senate President"
    LGA_CHAIRMAN = "local government chairman", "Local Government Chairman"
    COUNCILLOR = "councillor", "Councillor"
    SUG_PRESIDENT = "sug president", "SUG President"


class Position(models.Model):
    name = models.CharField(max_length=50, choices=PositionChoices.choices)
    election = models.ForeignKey(
        Election, on_delete=models.CASCADE, related_name="positions"
    )
    description = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.get_name_display()
