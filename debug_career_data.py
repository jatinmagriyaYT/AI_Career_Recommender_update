import os
import sys
import django

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AI_Career_Recommender.settings')
django.setup()

from ai_recommender.models import Career, CareerRecommendation, UserProfile

def check_career_data():
    print("--- Checking Career Data ---")
    
    # 1. Check 'General Physician'
    title = "General Physician"
    career = Career.objects.filter(title__icontains=title).first()
    
    if career:
        print(f"Found Career: '{career.title}'")
        print(f"Domain: '{career.domain}'")
        # print(f"Category: '{career.category}'") # Field does not exist
    else:
        print(f"❌ Career '{title}' NOT FOUND in DB.")

    # 2. Check User Recommendations
    # Get the latest user profile (assuming single user or valid one)
    # We'll just grab the first one with a recommendation
    rec = CareerRecommendation.objects.first()
    if rec:
        print(f"\nExample Recommendation:")
        print(f"User: {rec.user_profile.user.username}")
        print(f"Career: {rec.recommended_career.title}")
        print(f"Rec Domain: {getattr(rec.recommended_career, 'domain', 'N/A')}")
    else:
        print("No recommendations found.")

if __name__ == "__main__":
    check_career_data()
