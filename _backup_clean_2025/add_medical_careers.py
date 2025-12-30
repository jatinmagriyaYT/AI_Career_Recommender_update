
import pandas as pd
import os

# Define paths
dataset_path = 'datasets/career_dataset.csv'
backup_path = 'datasets/career_dataset_backup_v2.csv'

# New Medical Careers Data
medical_careers = [
    {
        'career_id': 'MED001',
        'career_name': 'Medical Doctor (General Practitioner)',
        'required_skills': 'Biology, Anatomy, Diagnosis, Patient Care, Medical Terminology, Pharmacology',
        'description': 'Diagnose and treat injuries or illnesses. examine patients; take medical histories; prescribe medications; and order, perform, and interpret diagnostic tests.',
        'education_required': 'Doctor of Medicine (MD)',
        'average_salary': 208000,
        'job_growth_rate': 3.0,
        'work_environment': 'Hospitals, Clinics, Private Practice',
        'related_fields': 'Healthcare, Biology, Science',
        'domain': 'Medical'
    },
    {
        'career_id': 'MED002',
        'career_name': 'Surgeon',
        'required_skills': 'Surgery, Anatomy, Hand-Eye Coordination, Biology, Critical Care, Medical Ethics',
        'description': 'Treat injuries, diseases, and deformities through operations. Using a variety of instruments, a surgeon corrects physical deformities, repairs bone and tissue after injuries, or performs preventive surgeries.',
        'education_required': 'Doctor of Medicine (MD) + Residency',
        'average_salary': 409665,
        'job_growth_rate': 3.0,
        'work_environment': 'Hospitals, Operating Rooms',
        'related_fields': 'Healthcare, Biology, Science',
        'domain': 'Medical'
    },
    {
        'career_id': 'MED003',
        'career_name': 'Nurse Practitioner',
        'required_skills': 'Nursing, Patient Care, Vital Signs, Biology, Compassion, Communication',
        'description': 'Serve as primary and specialty care providers, delivering advanced nursing services to patients and their families.',
        'education_required': 'Master of Science in Nursing (MSN)',
        'average_salary': 111680,
        'job_growth_rate': 45.0, # High growth!
        'work_environment': 'Hospitals, Clinics',
        'related_fields': 'Healthcare, Nursing',
        'domain': 'Medical'
    }
]

def add_medical_data():
    if not os.path.exists(dataset_path):
        print(f"Error: {dataset_path} not found.")
        return

    print(f"Loading {dataset_path}...")
    try:
        df = pd.read_csv(dataset_path)
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # Check if Doctor already exists
    if df['career_name'].str.contains("Doctor", case=False).any():
        print("Medical careers (Doctor) already seem to exist in the dataset.")
        # Proceed anyway to ensure these specific ones are present or update them? 
        # For now, let's just append if not exact matches.
    else:
        print("Doctor not found. Appending new data...")

    # Create DataFrame from new data
    new_df = pd.DataFrame(medical_careers)
    
    # Ensure columns match
    for col in df.columns:
        if col not in new_df.columns:
            new_df[col] = "" # Fill missing cols with empty string or defaults
            
    # Append
    combined_df = pd.concat([df, new_df], ignore_index=True)
    
    # Save backup
    if not os.path.exists(backup_path):
        df.to_csv(backup_path, index=False)
        print(f"Backed up original to {backup_path}")

    # Save new
    combined_df.to_csv(dataset_path, index=False)
    print(f"Successfully added {len(medical_careers)} medical careers to {dataset_path}")
    print("New Row Count:", len(combined_df))

if __name__ == "__main__":
    add_medical_data()
