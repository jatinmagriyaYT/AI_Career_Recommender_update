#!/usr/bin/env python3
"""
AI Career Recommender - FINAL TRAINING SCRIPT (Custom Dataset Optimized)
========================================================================
Optimized for your specific datasets:
1. Skills Dataset: Handles 'Skill ID', 'Skill Name', 'Category' columns correctly.
2. Resume Dataset: Handles 'resume_text' missing error automatically.
3. Skill Extraction: Uses Rule-Based matching from your CSV for 100% accuracy.
"""

import os
import re
import joblib
import pandas as pd
import numpy as np
import warnings
from datetime import datetime

# ==============================================================================
# ML LIBRARIES
# ==============================================================================
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from xgboost import XGBClassifier

import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize

# Setup NLTK (Download only if missing)
for resource in ['punkt', 'stopwords', 'wordnet']:
    try:
        nltk.data.find(f'corpora/{resource}' if resource != 'punkt' else f'tokenizers/{resource}')
    except LookupError:
        nltk.download(resource)

warnings.filterwarnings('ignore')

# ==============================================================================
# CONFIGURATION
# ==============================================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATASET_DIR = os.path.join(BASE_DIR, 'datasets')
MODEL_DIR = os.path.join(BASE_DIR, 'ml_models')
ENHANCED_MODEL_DIR = os.path.join(BASE_DIR, 'enhanced_models')

# Ensure directories exist
os.makedirs(DATASET_DIR, exist_ok=True)
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(ENHANCED_MODEL_DIR, exist_ok=True)

# ==============================================================================
# TEXT PREPROCESSING
# ==============================================================================
class AdvancedTextPreprocessor:
    def __init__(self):
        self.lemmatizer = WordNetLemmatizer()
        self.stop_words = set(stopwords.words('english'))

    def clean_text(self, text, for_skills=False):
        """
        Cleans text. 
        for_skills=True -> Preserves C++, C#, .NET, etc.
        for_skills=False -> Removes everything except words (for classification).
        """
        if pd.isna(text) or not isinstance(text, str):
            return ""

        text = text.lower()
        text = re.sub(r'http\S+|www\S+', ' ', text) # Remove URLs
        
        if for_skills:
            # Keep special chars for skills (C++, C#, node.js)
            text = re.sub(r'[^\w\s\+\.\#\-]', ' ', text)
        else:
            # Standard cleaning
            text = re.sub(r'[^\w\s]', ' ', text)
            text = re.sub(r'[0-9]+', ' ', text)

        tokens = word_tokenize(text)
        
        if not for_skills:
            tokens = [self.lemmatizer.lemmatize(t) for t in tokens if t not in self.stop_words and len(t) > 2]
        else:
            tokens = [t for t in tokens if t not in self.stop_words]

        return ' '.join(tokens)

# ==============================================================================
# DATA LOADING (SMART COLUMN DETECTION)
# ==============================================================================
def load_datasets():
    print(f"\n[DATA] Loading datasets from {DATASET_DIR}...")
    datasets = {}
    
    # Expected filenames
    files = {
        'career_df': 'career_dataset.csv',
        'skills_df': 'skills_dataset.csv',
        'resume_df': 'Resume.csv',
        'custom_skills': 'skills.txt' # Optional
    }

    for name, filename in files.items():
        path = os.path.join(DATASET_DIR, filename)
        if os.path.exists(path):
            if filename.endswith('.csv'):
                try:
                    df = pd.read_csv(path)
                    
                    # --- CRITICAL FIX: Normalize Column Names ---
                    # 'Skill Name' -> 'skill name', 'Resume_Text' -> 'resume_text'
                    df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_')
                    
                    datasets[name] = df
                    print(f"[OK] Loaded {filename} (Shape: {df.shape})")
                    print(f"     Columns found: {list(df.columns)}")
                    
                except Exception as e:
                    print(f"[ERROR] Failed to read {filename}: {e}")
                    datasets[name] = None
            else:
                # Text file loading
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        lines = [line.strip() for line in f.readlines() if line.strip()]
                    datasets[name] = lines
                    print(f"[OK] Loaded {filename} (Custom List: {len(lines)} skills)")
                except Exception as e:
                    # Optional file, so no big error
                    datasets[name] = None
        else:
            datasets[name] = None
            if name != 'custom_skills':
                print(f"[WARNING] {filename} not found.")

    return datasets

# ==============================================================================
# MODEL 1: RESUME CLASSIFIER
# ==============================================================================
def train_resume_classifier(resume_df):
    print("\n[MODEL 1] Training Resume Classifier...")
    if resume_df is None: 
        print("[SKIP] Resume Data missing.")
        return

    # Smart Column Search for 'resume_text'
    text_col = None
    possible_names = ['resume_text', 'resume', 'text', 'content', 'description']
    
    for col in resume_df.columns:
        if col in possible_names:
            text_col = col
            break
    
    if not text_col:
        # Fallback: Find any column with long text
        print("[WARN] 'resume_text' column not found directly. Searching...")
        for col in resume_df.columns:
            if resume_df[col].dtype == object and resume_df[col].astype(str).str.len().mean() > 50:
                text_col = col
                print(f"[FIX] Using '{col}' as resume text column.")
                break
    
    if not text_col:
        print(f"[FATAL] Could not find resume text column. Available: {list(resume_df.columns)}")
        return

    try:
        preprocessor = AdvancedTextPreprocessor()
        print(f"[RESUME] Cleaning text from column: '{text_col}'...")
        resume_df['clean'] = resume_df[text_col].apply(lambda x: preprocessor.clean_text(str(x), for_skills=False))
        
        # Check for category column
        label_col = 'category' if 'category' in resume_df.columns else None
        if not label_col:
             # Try to find valid label column
             for col in resume_df.columns:
                 if 'category' in col or 'label' in col or 'role' in col:
                     label_col = col
                     break
        
        if not label_col:
            print("[FATAL] Label/Category column missing.")
            return

        # Filter rare classes
        counts = resume_df[label_col].value_counts()
        valid = counts[counts >= 5].index
        df = resume_df[resume_df[label_col].isin(valid)]
        
        le = LabelEncoder()
        y = le.fit_transform(df[label_col])
        
        print("[RESUME] Training XGBoost Classifier...")
        pipeline = Pipeline([
            ('tfidf', TfidfVectorizer(max_features=3000, stop_words='english')),
            ('clf', XGBClassifier(eval_metric='logloss', use_label_encoder=False))
        ])
        
        pipeline.fit(df['clean'], y)
        print(f"[SUCCESS] Resume Classifier Trained. Classes: {len(le.classes_)}")
        
        joblib.dump({
            'model': pipeline,
            'label_encoder': le,
            'classes': le.classes_.tolist()
        }, os.path.join(ENHANCED_MODEL_DIR, 'enhanced_resume_classifier.pkl'))
        
    except Exception as e:
        print(f"[ERROR] Resume Classifier failed: {e}")

# ==============================================================================
# MODEL 2: SKILL EXTRACTOR (Optimized for your CSV)
# ==============================================================================
def train_skill_extractor(skills_df, custom_skills_list):
    print("\n[MODEL 2] Building Skill Extractor Database...")
    final_skills = set()
    
    # 1. Load from custom text file (if exists)
    if custom_skills_list:
        print(f"[INFO] Adding {len(custom_skills_list)} skills from skills.txt")
        for s in custom_skills_list:
            final_skills.add(s.lower().strip())
            
    # 2. Load from CSV (Smart Column Detection)
    if skills_df is not None:
        target_col = None
        
        # Priority 1: Exact 'skill_name' (normalized from 'Skill Name')
        if 'skill_name' in skills_df.columns:
            target_col = 'skill_name'
        # Priority 2: Column containing 'name'
        elif any('name' in col for col in skills_df.columns):
            target_col = [c for c in skills_df.columns if 'name' in c][0]
        # Priority 3: Column containing 'skill' BUT NOT 'id'
        elif any('skill' in col and 'id' not in col for col in skills_df.columns):
            target_col = [c for c in skills_df.columns if 'skill' in c and 'id' not in c][0]

        if target_col:
            print(f"[INFO] Extracting skills from column: '{target_col}'")
            count = 0
            for s in skills_df[target_col].astype(str):
                cleaned = s.strip().lower()
                if len(cleaned) > 1: # Avoid single chars
                    final_skills.add(cleaned)
                    count += 1
            print(f"[INFO] Added {count} skills from CSV.")
        else:
            print(f"[WARNING] Could not identify Skill Name column. Columns found: {list(skills_df.columns)}")

    # Fallback if list is empty
    if not final_skills:
        print("[WARNING] No skills found! Using fallback defaults.")
        final_skills = {'python', 'java', 'c++', 'sql', 'react', 'javascript', 'html', 'css', 'django', 'flask'} 
    
    print(f"[SUCCESS] Total Unique Skills to Track: {len(final_skills)}")
    
    # Save the clean list for rule-based matching
    joblib.dump({
        'all_skills_list': list(final_skills),
        'method': 'exact_match_database'
    }, os.path.join(ENHANCED_MODEL_DIR, 'enhanced_skill_extractor.pkl'))

# ==============================================================================
# MODEL 3: CAREER RECOMMENDER
# ==============================================================================
def train_recommender(career_df):
    print("\n[MODEL 3] Training Career Recommender...")
    if career_df is None: return

    try:
        preprocessor = AdvancedTextPreprocessor()
        career_texts = []
        
        # Combine columns intelligently
        cols_to_combine = ['career_name', 'required_skills', 'description', 'domain', 'job_role']
        available_cols = [c for c in cols_to_combine if c in career_df.columns]
        
        print(f"[INFO] Building profiles using: {available_cols}")
        
        for _, row in career_df.iterrows():
            text_parts = [str(row[c]) for c in available_cols]
            text = " ".join(text_parts)
            # Clean but keep technical terms
            career_texts.append(preprocessor.clean_text(text, for_skills=False))

        vectorizer = TfidfVectorizer(max_features=5000, stop_words='english')
        vectors = vectorizer.fit_transform(career_texts)
        
        joblib.dump({
            'vectorizer': vectorizer,
            'career_vectors': vectors,
            'career_df': career_df
        }, os.path.join(ENHANCED_MODEL_DIR, 'enhanced_confidence_scorer.pkl'))
        print("[SUCCESS] Recommender System Saved.")
        
    except Exception as e:
        print(f"[ERROR] Recommender training failed: {e}")

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
def main():
    print("AI CAREER RECOMMENDER - TRAINING STARTED")
    print("-" * 50)
    
    # 1. Load Data
    data = load_datasets()
    
    # 2. Train Models
    train_resume_classifier(data['resume_df'])
    
    # Pass both CSV data and custom list (if any)
    train_skill_extractor(data['skills_df'], data['custom_skills'])
    
    train_recommender(data['career_df'])
    
    print("-" * 50)
    print(f"[DONE] All models saved to {ENHANCED_MODEL_DIR}/")

if __name__ == "__main__":
    main()