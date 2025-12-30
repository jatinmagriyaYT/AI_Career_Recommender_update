import pandas as pd
import os

def update_skills_csv():
    # Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_path = os.path.join(base_dir, 'datasets', 'skills_dataset.csv')
    
    print(f"Loading {csv_path}...")
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Error loading CSV: {e}")
        return

    # Helper to get next ID
    try:
        last_id = df['skill_id'].max()
    except:
        last_id = 1000 # Fallback
        
    next_id = int(last_id) + 1
    
    # New Data
    new_skills_map = {
        'Core Clinical Skills': [
            'Patient Diagnosis', 'Treatment', 'Clinical Examination', 'Differential Diagnosis', 
            'Disease Management', 'Preventive Healthcare', 'Evidence-Based Medicine', 
            'Clinical Decision Making', 'Case History Taking', 'Treatment Planning'
        ],
        'Emergency & Critical Care': [
            'Emergency Medicine', 'Trauma Care', 'Basic Life Support (BLS)', 
            'Advanced Cardiac Life Support (ACLS)', 'First Aid', 'CPR', 
            'ICU Patient Management', 'Triage', 'Emergency Assessment'
        ],
        'Medical Knowledge': [
            'Internal Medicine', 'General Medicine', 'Pharmacology', 'Pathology Basics', 
            'Anatomy', 'Physiology', 'Clinical Research', 'Medical Ethics', 
            'Compliance', 'Infection Control', 'Public Health Awareness'
        ],
        'Patient Care': [
            'Patient Care', 'Patient Counseling', 'Doctor-Patient Communication', 
            'Empathy', 'Compassion', 'Mental Health Awareness', 'Palliative Care', 'Family Counseling'
        ],
        'Healthcare Management': [
            'Healthcare Management', 'Clinical Documentation', 'Electronic Medical Records (EMR)', 
            'Electronic Health Records (EHR)', 'Medical Report Writing', 'Hospital Administration', 
            'Quality Standards', 'Safety Standards', 'Medical Audits'
        ],
        'Medical Research': [
            'Medical Literature Review', 'Case Study Analysis', 'Research Methodology', 
            'Data Collection', 'Data Interpretation', 'Medical Writing'
        ],
        'Professional Skills': [
            'Leadership (Medical)', 'Team Coordination', 'Ethical Decision Making', 
            'Stress Management', 'Time Management', 'Continuous Learning'
        ]
    }
    
    new_rows = []
    
    existing_skills = set(df['skill_name'].str.lower().str.strip())
    
    for category, skills in new_skills_map.items():
        for skill in skills:
            if skill.lower().strip() in existing_skills:
                print(f"Skipping duplicate: {skill}")
                continue
                
            new_rows.append({
                'skill_id': next_id,
                'skill_name': skill,
                'category': category,
                'proficiency_levels': 'Intermediate',
                'related_careers': 'Doctor, Medical Professional, Nurse',
                'demand_level': 0.85
            })
            next_id += 1
            
    if new_rows:
        df_new = pd.DataFrame(new_rows)
        df_final = pd.concat([df, df_new], ignore_index=True)
        df_final.to_csv(csv_path, index=False)
        print(f"Success! Added {len(new_rows)} new skills.")
        print(df_final.tail(10))
    else:
        print("No new unique skills to add.")

if __name__ == "__main__":
    update_skills_csv()
