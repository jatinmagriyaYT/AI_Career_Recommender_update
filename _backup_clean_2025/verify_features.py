
import os
import django
import sys

# Setup Django Environment
sys.path.append(os.getcwd())
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AI_Career_Recommender.settings')
django.setup()

from ai_recommender.models import Career, TrendingJob, UserProfile, SkillAssessment
from ai_recommender.services import get_trending_jobs, analyze_skill_gap

def verify_backend():
    print("--- VERIFICATION START ---")

    # 1. Check Career Domain
    print("\n1. Checking Career Domain Field...")
    career_count = Career.objects.all().count()
    if career_count > 0:
        c = Career.objects.first()
        print(f"   Career '{c.title}' has domain: '{c.domain}'")
        if hasattr(c, 'domain'):
            print("   [PASS] Domain field exists.")
        else:
            print("   [FAIL] Domain field missing!")
    else:
        print("   [WARN] No careers found.")

    # 2. Check TrendingJob Model
    print("\n2. Checking TrendingJob Model...")
    # Clear old test data
    TrendingJob.objects.filter(job_title="Test Trend Job").delete()
    
    # Create a test trend
    t = TrendingJob.objects.create(
        job_title="Test Trend Job",
        domain="IT",
        trend_score=85,
        status='ACTIVE',
        required_skills="Python, Django, AI",
        trend_reason="Testing mechanism"
    )
    print(f"   Created TrendingJob: {t}")
    
    # Verify get_trending_jobs
    trends = get_trending_jobs(domain="IT")
    print(f"   get_trending_jobs('IT') returned {len(trends)} results.")
    
    found = False
    for job in trends:
        if job['title'] == "Test Trend Job":
            print("   [PASS] Created job found in service output.")
            found = True
            break
    if not found:
        print("   [FAIL] Created job NOT found in service output.")

    # 3. Check Skill Gap Analysis
    print("\n3. Checking Skill Gap Analysis...")
    # Create or get a user profile
    user_qs = UserProfile.objects.all()
    if user_qs.exists():
        profile = user_qs.first()
        print(f"   Using profile: {profile.user.username}")
        
        # Ensure profile has some skills
        if not profile.skills:
            profile.skills = "Python, HTML, CSS"
            profile.save()
            print("   Added temp skills to profile.")
            
        # Analyze against the test trend job (simulating it as a career for now, or use existing career)
        # We need a Career object for the function
        if career_count > 0:
            target_career = Career.objects.first()
            # update target career skills for test
            target_career.required_skills = "Python, Docker, Kubernetes"
            target_career.save()
            
            print(f"   Target Career: {target_career.title}")
            print(f"   Required: {target_career.required_skills}")
            print(f"   User Skills: {profile.skills}")
            
            analysis = analyze_skill_gap(profile, target_career)
            print("   Analysis Result:")
            print(analysis)
            
            if analysis['match_percentage'] >= 0:
                print("   [PASS] Analysis returned valid structure.")
            else:
                print("   [FAIL] Analysis failed.")
        else:
             print("   [WARN] Skipping Skill Gap test (no careers).")
    else:
        print("   [WARN] No user profiles found to test.")

    print("\n--- VERIFICATION END ---")

if __name__ == "__main__":
    verify_backend()
