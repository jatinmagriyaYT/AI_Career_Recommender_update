import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AI_Career_Recommender.settings')
# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

django.setup()

from ai_recommender.services import DOMAIN_SKILLS_MAP, CATEGORY_METADATA, extract_skills_from_text

def verify():
    print("Verifying Medical Data Integration...")
    
    # 1. Check DOMAIN_SKILLS_MAP
    med_skills = DOMAIN_SKILLS_MAP.get('medical', set())
    print(f"Medical Skills Count in Map: {len(med_skills)}")
    
    expected_skills = ['Patient Diagnosis', 'CPR', 'Internal Medicine', 'Medical Writing']
    # Check if they exist (case might vary in set, but keys should be title/original case)
    # The map uses the exact strings we put in.
    
    missing = [s for s in expected_skills if s not in med_skills]
    
    if missing:
        print(f"FAILED: Missing expected skills in map: {missing}")
    else:
        print("SUCCESS: Expected skills found in map.")
        
    # 2. Check CATEGORY_METADATA
    expected_cats = ['Core Clinical Skills', 'Emergency & Critical Care', 'Medical Research']
    missing_cats = [c for c in expected_cats if c not in CATEGORY_METADATA]
    
    if missing_cats:
        print(f"FAILED: Missing categories in metadata: {missing_cats}")
    else:
        print("SUCCESS: New categories found in metadata.")
        
    # 3. Test Extraction
    test_text = "Dr. John Doe is an expert in Patient Diagnosis, CPR, and Internal Medicine. He leads Clinical Research."
    extracted = extract_skills_from_text(test_text)
    print(f"\nTest Text: {test_text}")
    print(f"Extracted Skills: {extracted}")
    
    # Verify extraction
    required = ['Patient Diagnosis', 'CPR', 'Internal Medicine', 'Clinical Research']
    
    # Check for presence (fuzzy match or exact)
    extracted_set = set(extracted)
    # The extract_skills_from_text calls clean_skill_list which returns Title Case usually.
    
    found_count = 0
    for req in required:
        if req in extracted_set:
            found_count += 1
        else:
             print(f"  - Missed: {req}")
             
    if found_count == len(required):
         print("SUCCESS: Extraction working correctly.")
    else:
         print(f"FAILED: Only found {found_count}/{len(required)} skills.")

if __name__ == "__main__":
    verify()
