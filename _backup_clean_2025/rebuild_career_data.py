import os
import django
import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

# Setup Django Environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AI_Career_Recommender.settings')
django.setup()

from ai_recommender.models import Career

def rebuild_data():
    print("🚀 Starting Data Rebuild Process...")
    
    # 1. Fetch All Careers from DB
    print("🔹 Fetching careers from Database...")
    careers = Career.objects.all()
    
    if not careers.exists():
        print("❌ No careers found in Database! Aborting.")
        return

    data = []
    for c in careers:
        data.append({
            'career_id': c.id,
            'career_name': c.title,
            'description': c.description,
            'required_skills': c.required_skills,
            'education_required': c.education_required,
            'average_salary': c.average_salary,
            'job_growth_rate': c.job_growth_rate,
            'domain': c.domain,
            'job_role': getattr(c, 'job_role', ''),
            'challenges': getattr(c, 'challenges', '')
        })
    
    df = pd.DataFrame(data)
    print(f"✅ Loaded {len(df)} careers from DB.")
    
    # 2. Save to CSV (Source of Truth for Pandas)
    csv_path = 'career_dataset.csv'
    df.to_csv(csv_path, index=False)
    print(f"✅ Saved updated dataset to {csv_path}")
    
    # 3. Re-Train ML Models (Vectors)
    print("🔹 Training TF-IDF Vectorizer...")
    
    # Combine relevant text fields for vectorization
    # We want to match against skills, education, and domain
    df['text_content'] = df['domain'].fillna('') + " " + \
                         df['required_skills'].fillna('') + " " + \
                         df['education_required'].fillna('')
    
    vectorizer = TfidfVectorizer(stop_words='english', max_features=5000)
    career_vectors = vectorizer.fit_transform(df['text_content'])
    
    print(f"✅ Created Career Vectors: Shape {career_vectors.shape}")
    
    # 4. Save Models (PKL)
    model_data = {
        'vectorizer': vectorizer,
        'career_vectors': career_vectors
    }
    
    os.makedirs('enhanced_models', exist_ok=True)
    model_path = 'enhanced_models/enhanced_confidence_scorer.pkl'
    joblib.dump(model_data, model_path)
    print(f"✅ Saved ML models to {model_path}")
    
    print("\n🎉 REBUILD COMPLETE! The system is now fully synced.")
    print("👉 Please RESTART your server to load the new models.")

if __name__ == '__main__':
    rebuild_data()
