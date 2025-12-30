
import pandas as pd
from django.core.management.base import BaseCommand
from ai_recommender.models import Career
from ai_recommender.services import CAREER_DF

class Command(BaseCommand):
    help = 'Syncs the Career database table with the current CSV dataset (CAREER_DF).'

    def handle(self, *args, **options):
        self.stdout.write("Starting Career DB Sync...")
        
        if CAREER_DF is None or CAREER_DF.empty:
            self.stdout.write(self.style.ERROR("CAREER_DF is empty. Cannot sync."))
            return

        count_created = 0
        count_updated = 0
        
        for _, row in CAREER_DF.iterrows():
            title = row.get('career_name', '').strip()
            if not title:
                continue
                
            # Safely get fields
            desc = row.get('description', 'No description available')
            req_skills = row.get('required_skills', '')
            edu = row.get('education_required', 'Not specified')
            salary = row.get('average_salary', 0)
            growth = row.get('job_growth_rate', 0)
            env = row.get('work_environment', 'Office')
            related = row.get('related_fields', '')
            domain = row.get('domain', 'General') # Ensure domain is synced

            try:
                # Type safe conversion
                salary = float(str(salary).replace('$', '').replace(',', '')) if salary else 0
                growth = float(str(growth).replace('%', '')) if growth else 0
            except ValueError:
                salary = 0
                growth = 0

            target_career, created = Career.objects.update_or_create(
                title=title,
                defaults={
                    'description': desc,
                    'required_skills': req_skills,
                    'education_required': edu,
                    'average_salary': salary,
                    'job_growth_rate': growth,
                    'work_environment': env,
                    'related_fields': related,
                    'domain': domain
                }
            )
            
            if created:
                count_created += 1
            else:
                count_updated += 1
                
        self.stdout.write(self.style.SUCCESS(f"Sync Complete. Created: {count_created}, Updated: {count_updated}"))
