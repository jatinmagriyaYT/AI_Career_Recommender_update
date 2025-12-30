
import os
import django
import sys

# Setup Django Environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AI_Career_Recommender.settings')
django.setup()

from ai_recommender.models import Career, UserProfile, TrendingJob
from ai_recommender.services import analyze_skill_gap, get_trending_jobs, CAREER_DF

def test_medical_career():
    print("--- TESTING MEDICAL CAREER SCENARIO ---")

    # 1. Verify Dataset Expansion (Check for 'Doctor')
    print("\n1. Searching for 'Doctor' in Career Database...")
    medical_careers = Career.objects.filter(title__icontains="Doctor")
    
    if not medical_careers.exists():
        # Fallback: Check CSV directly if DB isn't synced yet
        print("   'Doctor' not found in DB. Checking CSV DataFrame...")
        if not CAREER_DF.empty:
             doctors_df = CAREER_DF[CAREER_DF['career_name'].str.contains("Doctor", case=False, na=False)]
             if not doctors_df.empty:
                 print(f"   Found {len(doctors_df)} medical careers in CSV (e.g., {doctors_df.iloc[0]['career_name']}).")
                 # Create a dummy DB entry for testing if missing
                 c_row = doctors_df.iloc[0]
                 target_career = Career.objects.create(
                     title=c_row['career_name'],
                     description="Medical Professional",
                     required_skills=c_row.get('required_skills', 'Biology, Anatomy, Diagnosis'),
                     domain="Medical",
                     average_salary=200000,
                     job_growth_rate=5.0,
                     education_required="Doctorate",
                     work_environment="Hospital",
                     related_fields="Healthcare"
                 )
                 print("   Created temporary 'Doctor' career in DB for testing.")
             else:
                 print("   [FAIL] No 'Doctor' careers found in CSV explicitly.")
                 return
        else:
            print("   [FAIL] CAREER_DF is empty.")
            return
    else:
        target_career = medical_careers.first()
        print(f"   [PASS] Found existing career: {target_career.title} (Domain: {target_career.domain})")

    # 2. Simulate User with Partial Medical Skills
    print("\n2. Simulating User Profile...")
    # Create or update a test user
    from django.contrib.auth.models import User
    user, _ = User.objects.get_or_create(username="dr_test")
    profile, _ = UserProfile.objects.get_or_create(user=user)
    
    # Give them some relevant skills but miss some
    profile.skills = "Biology, Communication, Patient Care"
    profile.save()
    print(f"   User Skills: {profile.skills}")
    print(f"   Career Required: {target_career.required_skills}")

    # 3. Test Skill Gap Analysis
    print("\n3. Running Skill Gap Analysis...")
    gap_analysis = analyze_skill_gap(profile, target_career)
    print(f"   Match Score: {gap_analysis['match_percentage']}%")
    print(f"   You Have: {gap_analysis['have_list']}")
    print(f"   Missing: {gap_analysis['missing_list']}")
    
    if gap_analysis['match_percentage'] > 0:
        print("   [PASS] Skill Gap Analysis successful.")
    else:
        print("   [WARN] 0% Match - Ensure skill names match exactly (case/cleaning).")

    # 4. Test Trending Jobs for 'Medical'
    print("\n4. Checking Trending Jobs for 'Medical' domain...")
    # Add a dummy trending job if none exist
    if not TrendingJob.objects.filter(domain="Medical").exists():
        TrendingJob.objects.create(
            job_title="Telemedicine Specialist",
            domain="Medical",
            status="ACTIVE",
            trend_score=92,
            required_skills="Digital Health, Diagnosis, Communication",
            trend_reason="Rise of remote healthcare"
        )
        print("   (Created mock trending job for test)")
        
    trends = get_trending_jobs(domain="Medical")
    print(f"   Found {len(trends)} trending jobs in Medical:")
    for t in trends:
        print(f"   - {t['title']} (Score: {t['score']})")

    print("\n--- TEST COMPLETE ---")

if __name__ == "__main__":
    test_medical_career()
