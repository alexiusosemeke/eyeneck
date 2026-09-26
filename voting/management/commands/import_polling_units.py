import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction # transaction helps us guarantees the database operation is executed as one so it's either it completes or it fails (This is helpful when we are importing a large number of data and we want to ensure that if any error occurs during the import, the entire operation is rolled back and no partial data is saved to the database) 

from voting.models import PollingUnit, Ward, LGA, State


class Command(BaseCommand):
    help = 'Import polling units from a CSV file'
    
    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Import started...")
        
        csv_file = (Path(__file__).resolve().parents[2]/"data"/"polling-units.csv")
        
        if not csv_file.exists():
            self.stderr.write("CSV file not found.")
            return
        
        imported = 0
        
        with open(csv_file, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                state, _ = State.objects.get_or_create(
                    name=row["state_name"].strip().title(),
                )

                lga, _ = LGA.objects.get_or_create(
                    name=row["local_government_name"].strip().title(),
                    state=state,
                )

                ward, _ = Ward.objects.get_or_create(
                    name=row["ward_name"].strip().title(),
                    lga=lga,
                )
                
                PollingUnit.objects.get_or_create(
                    name=row["name"],
                    ward=ward,
                    defaults={
                        "latitude": row["location.latitude"] or None,
                        "longitude": row["location.longitude"] or None,
                    },
                )

                imported += 1

                if imported % 5000 == 0:
                    self.stdout.write(f"{imported} rows processed...")

        self.stdout.write(
            self.style.SUCCESS(
                f"Import completed successfully. {imported} rows processed."
            )
        )