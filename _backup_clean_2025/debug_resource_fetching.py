import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AI_Career_Recommender.settings')
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
django.setup()

from ai_recommender.services import fetch_youtube_resources

def debug_fetch():
    print("Debugging fetch_youtube_resources...")
    
    print(f"Function Location: {fetch_youtube_resources}")
    skills = ['Anatomy', 'General Medicine', 'CPR']
    domain = 'medical'
    career = 'Doctor'
    
    for skill in skills:
        print(f"\n--- Testing Skill: {skill} (Domain: {domain}) ---")
        try:
            # We need to temporarily modify the function or just rely on its output.
            # Since I can't modify it easily for debugging logging without editing the file,
            # I will just run it and see if it returns anything.
            # If it returns empty list for CPR, we know it's being filtered (since API key works).
            
            resources = fetch_youtube_resources(skill, domain=domain, career_context=career, max_results=3)
            print(f"Resources found: {len(resources)}")
            for res in resources:
                print(f" - {res['title']} ({res['url']})")
                
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    debug_fetch()
