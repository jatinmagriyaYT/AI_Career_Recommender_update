import os
import sys
import django
from django.db.models import Q

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AI_Career_Recommender.settings')
django.setup()

from ai_recommender.models import Career

def fix_domains():
    print("--- Fixing Career Domains ---")
    
    # 1. MEDICAL
    medical_keywords = ['Doctor', 'Physician', 'Surgeon', 'Nurse', 'Medical', 'Clinical', 'Health', 'Patient', 'Hospital']
    medical_careers = Career.objects.filter(
        Q(title__icontains='Doctor') | 
        Q(title__icontains='Physician') |
        Q(title__icontains='Surgeon') |
        Q(title__icontains='Nurse') |
        Q(title__icontains='Medical')
    )
    
    count_med = 0
    for career in medical_careers:
        if career.domain != 'Medical':
            print(f"Updating '{career.title}': '{career.domain}' -> 'Medical'")
            career.domain = 'Medical'
            career.save()
            count_med += 1
            
    # 2. LEGAL
    legal_careers = Career.objects.filter(
        Q(title__icontains='Lawyer') | 
        Q(title__icontains='Advocate') |
        Q(title__icontains='Legal') |
        Q(title__icontains='Attorney') |
        Q(title__icontains='Judge')
    )
    
    count_leg = 0
    for career in legal_careers:
        if career.domain != 'Legal':
            print(f"Updating '{career.title}': '{career.domain}' -> 'Legal'")
            career.domain = 'Legal'
            career.save()
            count_leg += 1
            
    print(f"\nSummary:")
    print(f"Updated {count_med} Medical careers.")
    print(f"Updated {count_leg} Legal careers.")

if __name__ == "__main__":
    fix_domains()
