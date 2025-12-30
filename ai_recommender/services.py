import pandas as pd

import numpy as np

import joblib

import re

import requests



from django.core.cache import cache

from django.conf import settings

import PyPDF2

from docx import Document





from sklearn.metrics.pairwise import cosine_similarity



from .models import UserProfile, Career, PersonalityAssessment, SkillAssessment, CareerRecommendation, TrendingJob

from .utils import (

    clean_skill_list, clean_title_for_merge, smart_split_skills, 

    format_salary, get_default_salary, get_default_salary_by_title,

    get_default_growth_by_title, calculate_demand_level, 

    generate_demand_level_by_title, safe_load_df, normalize_skill

)



# --- GLOBAL DATA LOADING ---

try:

    # --- HERE ARE THE GLOBAL DATA FRAMES (WITH COLUMN NORMALIZATION) ---

    CAREER_DF = safe_load_df('career_dataset.csv')

    if CAREER_DF is None:

        CAREER_DF = safe_load_df('datasets/career_dataset_final.csv')



    if CAREER_DF is None or CAREER_DF.empty:
        raise FileNotFoundError("Career data not found!")
    
    # Ensure numeric columns are actually numeric
    numeric_cols = ['job_growth_rate', 'average_salary']
    for col in numeric_cols:
        if col in CAREER_DF.columns:
            CAREER_DF[col] = pd.to_numeric(CAREER_DF[col], errors='coerce').fillna(0)

    

    CAREER_DF['clean_key'] = CAREER_DF.get('career_name', pd.Series(['Unknown'] * len(CAREER_DF))).apply(clean_title_for_merge)

    

    CAREER_DF.drop_duplicates(subset=['clean_key'], keep='first', inplace=True)



    SKILLS_DF = safe_load_df('skills_dataset.csv')

    PERSONALITY_DF = safe_load_df('personality.csv')



    # ----------------------------------------

except Exception as e:

    print(f"FATAL ERROR: Could not load core datasets: {e}")

    CAREER_DF = pd.DataFrame(columns=['career_name', 'required_skills', 'description', 'career_id', 'education_required', 'average_salary', 'clean_key']) 

    SKILLS_DF = pd.DataFrame(columns=['skill_id', 'skill_name', 'category'])





# Load ML models (with error handling)

models_loaded = False

try:

    # Use the 'enhanced' models from the training script

    SKILL_EXTRACTOR_DATA = joblib.load('enhanced_models/enhanced_skill_extractor.pkl')

    CONFIDENCE_SCORER_DATA = joblib.load('enhanced_models/enhanced_confidence_scorer.pkl')

    

    # The skill extractor is now just a clean list of skills

    SKILL_LIST = SKILL_EXTRACTOR_DATA['all_skills_list']

    

    VECTORIZER = CONFIDENCE_SCORER_DATA['vectorizer']

    CAREER_VECTORS = CONFIDENCE_SCORER_DATA['career_vectors']

    

    models_loaded = True

except Exception as e:

    print(f"Warning: Could not load ENHANCED ML models: {e}")

    print("Some features will be limited. Please run 'python train_models.py'.")





# --- SKILL CATEGORIZATION ---



def get_skill_category_map():

    """

    [HINGLISH]

    Use: Ye function `group_skills_by_category` me use hota h.

    Why: Skills ko unki category (e.g., Python -> Programming Language) se map karne ke liye.

    Effect: Isse hum skills ko sahi group me dikha paate h.

    """

    global SKILLS_DF

    category_map = {}

    

    # Ensure SKILLS_DF has the required normalized columns

    if SKILLS_DF is not None and not SKILLS_DF.empty and 'skill_name' in SKILLS_DF.columns and 'category' in SKILLS_DF.columns:

        for _, row in SKILLS_DF.iterrows():

            skill = str(row['skill_name']).strip().lower()

            category = str(row['category']).strip()

            if skill and category:

                category_map[skill] = category

    return category_map



# Define Category Metadata for HTML styling

CATEGORY_METADATA = {

    'Programming Languages': {'icon': 'code', 'color_class': 'prog'},

    'Frameworks': {'icon': 'microchip', 'color_class': 'info'},

    'Databases': {'icon': 'database', 'color_class': 'db'},

    'Cloud Platforms': {'icon': 'cloud', 'color_class': 'cloud'},

    'DevOps': {'icon': 'cogs', 'color_class': 'tools'},

    'Soft Skills': {'icon': 'handshake', 'color_class': 'secondary'},

    # Add your specific categories here if needed

    'Other': {'icon': 'tag', 'color_class': 'secondary'},

    # --- MEDICAL CATEGORIES ---
    'Core Clinical Skills': {'icon': 'user-md', 'color_class': 'medical-primary'},
    'Emergency & Critical Care': {'icon': 'ambulance', 'color_class': 'medical-danger'},
    'Medical Knowledge': {'icon': 'book-medical', 'color_class': 'medical-info'},
    'Patient Care': {'icon': 'heartbeat', 'color_class': 'medical-success'},
    'Healthcare Management': {'icon': 'hospital', 'color_class': 'medical-warning'},
    'Medical Research': {'icon': 'microscope', 'color_class': 'medical-dark'},
    'Professional Skills': {'icon': 'user-tie', 'color_class': 'medical-secondary'},
}



def group_skills_by_category(profile_skills_list):

    """

    [HINGLISH]

    Use: Ye `views.py` me resume upload page par skills ko categorize karke dikhane ke liye use hota h.

    Why: Agar saare skills ek list me honge to user confuse ho jayega. Grouping se UI clean lagta h.

    Effect: User ko apne skills organized way me dikhte h (e.g., Languages alag, Tools alag).

    """

    skill_to_category_map = get_skill_category_map()

    categorized_skills = {}



    for skill_display_name in profile_skills_list:

        # Use lowercased version for lookup in the map

        skill_key = skill_display_name.lower()

        # Fallback to general category if exact match not found

        category_name = skill_to_category_map.get(skill_key, 'Other')

        

        # Get metadata for styling (for HTML use)

        category_info = CATEGORY_METADATA.get(category_name, CATEGORY_METADATA['Other'])



        if category_name not in categorized_skills:

            categorized_skills[category_name] = {

                'info': category_info,

                'skills': []

            }

        

        # Append the display name (Title Cased)

        categorized_skills[category_name]['skills'].append(skill_display_name)

    

    # Sort categories alphabetically

    return dict(sorted(categorized_skills.items()))





# --- RESUME ANALYSIS ---



def analyze_resume_file(resume_file):

    """

    [HINGLISH]

    Use: Ye `views.py` me jab user resume upload karta h tab use hota h.

    Why: Resume (PDF/Docx) se text padh kar usme se skills aur experience extract karne ke liye.

    Effect: User ko manually form nahi bharna padta, resume se data auto-fill ho jata h.

    """

    text = ''

    try:

        if resume_file.name.endswith('.pdf'):

            reader = PyPDF2.PdfReader(resume_file)

            text = ' '.join([page.extract_text() for page in reader.pages if page.extract_text()])

        elif resume_file.name.endswith('.docx'):

            doc = Document(resume_file)

            text = ' '.join([paragraph.text for paragraph in doc.paragraphs])

        else:

            return {'error': 'Unsupported file type.'}



        if not text.strip():

            return {'error': 'No text could be extracted from the file'}



        # Use the new robust extraction function

        skills_clean = extract_skills_from_text(text)



        experience_years = 0

        matches = re.findall(r'(\d+)\s*(?:year|yr|years|yrs)\s*(?:of)?\s*(?:exp|experience)', text, re.IGNORECASE)

        if matches:

            experience_years = max(int(m) for m in matches)



        return {

            'skills': skills_clean,

            'experience_years': experience_years,

            'analysis_method': 'enhanced_rule_match'

        }

    except Exception as e:

        import traceback

        traceback.print_exc()

        return {'error': f'Analysis error: {str(e)}'}



# --- SKILL EXTRACTION LOGIC ---



# --- DOMAIN & SKILL CONSTANTS ---
# --- DOMAIN & SKILL CONSTANTS ---
DOMAIN_INDICATORS = {
    'medical': ['mbbs', 'md', 'doctor', 'medicine', 'surgery', 'hospital', 'clinical', 'patient', 'health', 'anatomy', 'pharmacy', 'nursing', 'dr.', 'healthcare', 'medical'],
    'legal': ['llb', 'llm', 'law', 'legal', 'advocate', 'court', 'litigation', 'judge', 'compliance', 'corporate law', 'bar council'],
    'finance': ['b.com', 'm.com', 'ca', 'cpa', 'finance', 'account', 'audit', 'tax', 'economics', 'banking', 'investment', 'chartered'],
    'arts': ['b.a', 'm.a', 'fine arts', 'design', 'creative', 'visual', 'graphic', 'fashion', 'writer', 'literature', 'history', 'arts'],
    'defense': ['nda', 'cds', 'army', 'navy', 'defense', 'military', 'air force', 'combat', 'security', 'soldier', 'lieutenant'],
    'engineering': ['b.tech', 'm.tech', 'engineering', 'computer science', 'mechanical', 'civil', 'electrical', 'software', 'developer', 'be', 'b.e.', 'technology', 'it'],
    'sales_marketing': ['mba', 'bba', 'marketing', 'sales', 'seo', 'digital marketing', 'business development', 'crm', 'management'],
}

DOMAIN_SKILLS_MAP = {
        'medical': {
            # Core Clinical
            'Patient Diagnosis', 'Treatment', 'Clinical Examination', 'Differential Diagnosis', 
            'Disease Management', 'Preventive Healthcare', 'Evidence-Based Medicine', 
            'Clinical Decision Making', 'Case History Taking', 'Treatment Planning',
            
            # Emergency
            'Emergency Medicine', 'Trauma Care', 'Basic Life Support (BLS)', 
            'Advanced Cardiac Life Support (ACLS)', 'First Aid', 'CPR', 
            'ICU Patient Management', 'Triage', 'Emergency Assessment',
            
            # Knowledge
            'Internal Medicine', 'General Medicine', 'Pharmacology', 'Pathology Basics', 
            'Anatomy', 'Physiology', 'Clinical Research', 'Medical Ethics', 
            'Compliance', 'Infection Control', 'Public Health Awareness',
            
            # Patient Care
            'Patient Care', 'Patient Counseling', 'Doctor-Patient Communication', 
            'Empathy', 'Compassion', 'Mental Health Awareness', 'Palliative Care', 'Family Counseling',
            
            # Management
            'Healthcare Management', 'Clinical Documentation', 'Electronic Medical Records (EMR)', 
            'Electronic Health Records (EHR)', 'Medical Report Writing', 'Hospital Administration', 
            'Quality Standards', 'Safety Standards', 'Medical Audits',
            
            # Research
            'Medical Literature Review', 'Case Study Analysis', 'Research Methodology', 
            'Data Collection', 'Data Interpretation', 'Medical Writing',
            
            # Professional
            'Leadership (Medical)', 'Team Coordination', 'Ethical Decision Making', 
            'Stress Management', 'Time Management', 'Continuous Learning',
            
            # Legacy/Existing
            'Medicine', 'Surgery', 'Diagnostics', 'Pharmacy', 'Medical Terminology', 
            'Radiology', 'Pathology', 'Nursing', 'Pediatrics', 'Cardiology', 
            'Neurology', 'Oncology', 'Biochemistry', 'Microbiology', 'Anesthesiology', 'Dermatology'
        },
        'legal': {
            'Legal Research', 'Litigation', 'Corporate Law', 'Drafting', 'Compliance', 
            'Contract Law', 'Intellectual Property', 'Legal Writing', 'Negotiation', 
            'Civil Law', 'Criminal Law', 'Arbitration', 'Mediation', 'Case Analysis'
        },
        'finance': {
            'Accounting', 'Financial Analysis', 'Auditing', 'Taxation', 'Budgeting', 
            'Risk Management', 'Financial Reporting', 'QuickBooks', 'Excel', 'Data Analysis',
            'Investment Banking', 'Portfolio Management', 'Economics', 'GST', 'Tally'
        },
        'arts': {
            'Graphic Design', 'Visual Arts', 'Creative Writing', 'Illustration', 'Photoshop', 
            'Illustrator', 'InDesign', 'User Experience (UX)', 'User Interface (UI)', 
            'Animation', 'Photography', 'Video Editing', 'Content Creation', 'Storytelling'
        },
        'defense': {
            'Leadership', 'Strategic Planning', 'Risk Assessment', 'Security Operations', 
            'Emergency Management', 'Team Management', 'Logistics', 'Operational Planning', 
            'Physical Fitness', 'Weapons Handling', 'Surveillance', 'Crisis Management'
        },
        'sales_marketing': {
            'Digital Marketing', 'SEO', 'SEM', 'Content Marketing', 'Sales Strategy', 
            'CRM', 'Lead Generation', 'Market Research', 'Social Media Marketing', 
            'Brand Management', 'Public Relations', 'Negotiation', 'Communication', 
            'Customer Relationship Management', 'Email Marketing'
        },
        'engineering': {
            # Core Engineering (Non-CS)
            'Mechanical Design', 'CAD', 'SolidWorks', 'AutoCAD', 'Thermodynamics', 'Fluid Mechanics',
            'Civil Engineering', 'Structural Analysis', 'Surveying', 'Concrete Technology',
            'Electrical Circuits', 'PCB Design', 'Embedded Systems', 'Matlab', 'Simulink',
            # Tech / CS (Keep robust list)
            'Python', 'Java', 'C++', 'C#', 'JavaScript', 'React', 'Angular', 'Node.js', 
            'Django', 'Flask', 'SQL', 'AWS', 'Docker', 'Kubernetes', 'Machine Learning', 
            'Data Analysis', 'Git', 'Linux', 'Software Development', 'Algorithms', 'Web Development',
            'Android', 'iOS', 'Flutter', 'React Native', 'MongoDB', 'PostgreSQL',
            'Artificial Intelligence', 'Data Science', 'Cloud Computing', 'Cyber Security'
        },
        'general': {
            # Soft Skills & Basics (Safe for everyone)
            'Communication', 'Leadership', 'Teamwork', 'Problem Solving', 'Time Management', 
            'Microsoft Office', 'Excel', 'Word', 'PowerPoint', 'Writing', 'Research', 
            'Critical Thinking', 'Adaptability', 'English', 'Management'
        }
    }

# Skills that should NOT trigger technical career matches on their own
SOFT_SKILLS_BLOCKLIST = {
    'leadership', 'management', 'communication', 'writing', 'teamwork', 'problem solving', 
    'time management', 'research', 'critical thinking', 'adaptability', 'english', 
    'microsoft office', 'excel', 'word', 'powerpoint', 'project management'
}

def detect_user_domain(profile_text, profile_skills_list):
    """
    STRICT Domain Detection.
    Determines the user's primary domain to LOCK recommendations.
    Returns: 'medical', 'engineering', 'legal', etc. OR 'general'
    """
    text_lower = profile_text.lower()
    
    # 1. STRONG SIGNAL: Check Education explicitly
    # This overrides everything else. If they did MBBS, they are Medical.
    if re.search(r'\b(mbbs|md|doctor of medicine|bds|bams|bhms)\b', text_lower):
        return 'medical'
    if re.search(r'\b(llb|llm|b\.a\.llb)\b', text_lower):
        return 'legal'
    if re.search(r'\b(b\.tech|m\.tech|b\.e\.|m\.e\.|bca|mca)\b', text_lower):
        return 'engineering'
    
    # 2. Check explicitly defined DOMAIN_INDICATORS in resume text
    domain_scores = {d: 0 for d in DOMAIN_INDICATORS}
    
    for domain, keywords in DOMAIN_INDICATORS.items():
        for kw in keywords:
            # Word boundary search
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                domain_scores[domain] += 2 # Stronger weight for keywords in text
                
    # 3. Check Skills Distribution
    for skill in profile_skills_list:
        # Check if it's a string or object (handling both cases)
        if isinstance(skill, str):
            s_lower = skill.lower()
        else:
             s_lower = skill.skill_name.lower() if hasattr(skill, 'skill_name') else str(skill).lower()

        if s_lower in SOFT_SKILLS_BLOCKLIST:
            continue # Ignore soft skills for domain detection
            
        for domain, skills in DOMAIN_SKILLS_MAP.items():
            if domain == 'general': continue
            if any(s.lower() == s_lower for s in skills):
                domain_scores[domain] += 1

    # 4. Determine Winner
    # Filter out domains with 0 score
    active_domains = {k: v for k, v in domain_scores.items() if v > 0}
    
    if not active_domains:
        return 'general'
        
    # Get the domain with maximum score
    primary_domain = max(active_domains, key=active_domains.get)
    
    # Threshold check: Must have at least some signal to leave 'general'
    if active_domains[primary_domain] < 1:
        return 'general'
        
    print(f"DEBUG: Domain Detection Scores: {active_domains} -> Winner: {primary_domain}")
    return primary_domain


def compute_skill_overlap(user_skills, required_skills_text, is_tech_role=False):
    """
    Calculates HARD overlap between user skills and career requirements.
    Optionally ignore soft skills for tech roles.
    Returns: (overlap_count, overlap_percentage, missing_critical_skills)
    """
    if not required_skills_text or not isinstance(required_skills_text, str):
        return 0, 0, []

    # Get sets
    req_list = [s.strip().lower() for s in required_skills_text.split(',') if s.strip()]
    req_set = set(req_list)
    
    if not req_set:
        return 0, 0, []

    # Filter user skills if tech role
    if is_tech_role:
        user_set = {
            s.skill_name.lower() for s in user_skills 
            if s.skill_name.lower() not in SOFT_SKILLS_BLOCKLIST
        }
    else:
        user_set = {s.skill_name.lower() for s in user_skills}
    
    # Calculate overlap
    intersection = req_set.intersection(user_set)
    count = len(intersection)
    percentage = (count / len(req_set)) * 100
    
    missing = list(req_set - user_set)
    
    return count, percentage, missing


def extract_skills_from_text(text):
    """
    Robust skill extraction with IN-PLACE DOMAIN DETECTION.
    Uses global DOMAIN_SKILLS_MAP.
    """
    if not text:
        return []
        
    text_lower = text.lower()
    text_clean = re.sub(r'[,/()\[\]]', ' ', text_lower)
    
    detected_domains = set()
    for domain, keywords in DOMAIN_INDICATORS.items():
        for kw in keywords:
            if re.search(r'\b' + re.escape(kw) + r'\b', text_clean):
                detected_domains.add(domain)

    if not detected_domains:
        detected_domains.add('general')
        
    print(f"DEBUG: Detected Domains for Extraction: {detected_domains}")

    search_list = set()
    search_list.update(DOMAIN_SKILLS_MAP['general'])

    for domain in detected_domains:
        if domain in DOMAIN_SKILLS_MAP:
            search_list.update(DOMAIN_SKILLS_MAP[domain])

    if 'engineering' in detected_domains and models_loaded and 'SKILL_LIST' in globals():
        for s in SKILL_LIST:
            if len(str(s)) > 2:
                search_list.add(str(s).lower())

    skills_found = set()
    sorted_skills = sorted(list(search_list), key=len, reverse=True)
    
    for skill in sorted_skills:
        pattern = r'(?:^|[\s,./(\[])' + re.escape(skill.lower()) + r'(?:$|[\s,./)\]])'
        if re.search(pattern, text_clean):
            skills_found.add(skill)

    if 'engineering' in detected_domains:
        if re.search(r'\bc\b', text_clean):
             if re.search(r'c\s+programming|language|developer', text_clean) or re.search(r',\s*c\s*,', text_clean):
                 skills_found.add('C')
    
    return clean_skill_list(list(skills_found))





# --- PERSONALITY LOGIC ---



def calculate_personality_scores(post_data):

    """

    [HINGLISH]

    Use: Ye `views.py` me personality test submit hone par use hota h.

    Why: User ke answers (1-5 scale) ko Big Five traits (Extraversion, etc.) me convert karne ke liye.

    Effect: Hame user ki personality ka score milta h jo career matching me help karta h.

    """

    scores = {

        'extraversion': 0,

        'agreeableness': 0,

        'conscientiousness': 0,

        'emotional_stability': 0,

        'openness': 0

    }

    

    # Correct mapping for the 10 questions to the Big Five traits

    trait_map = {

        'extraversion': [1, 6],

        'agreeableness': [2, 7],

        'conscientiousness': [3, 8],

        'emotional_stability': [4, 9],

        'openness': [5, 10],

    }

    

    # Calculate scores based on the actual question numbers

    for trait, q_nums in trait_map.items():

        for q_num in q_nums:

            # Safely get the score (default to 3 if missing or invalid)

            score = int(post_data.get(f'question_{q_num}', 3))

            scores[trait] += score

    

    # Normalize scores to 1-10 scale (since total is 10 max per trait)

    for trait in scores.keys():

        scores[trait] = max(1, min(10, scores[trait])) 



    return scores



def determine_mbti_type(scores):

    """

    [HINGLISH]

    Use: Ye `views.py` me personality result calculate karte waqt use hota h.

    Why: Big Five scores ko MBTI type (e.g., INTJ, ENFP) me convert karne ke liye.

    Effect: User ko ek familiar personality type milta h jo career matching me use hota h.

    """

    # Simplified mapping (not scientifically accurate but functional for this app)

    # E/I based on Extraversion (score >= 6 for E)

    e_i = 'E' if scores['extraversion'] >= 6 else 'I'

    # S/N based on Openness (score >= 6 for N)

    s_n = 'N' if scores['openness'] >= 6 else 'S'

    # T/F based on Conscientiousness/Agreeableness (High Conscientiousness/Low Agreeableness for T)

    t_f = 'T' if scores['conscientiousness'] >= 6 and scores['agreeableness'] < 6 else 'F'

    # J/P based on Conscientiousness (score >= 6 for J)

    j_p = 'J' if scores['conscientiousness'] >= 6 else 'P'

    

    return f"{e_i}{s_n}{t_f}{j_p}"



def get_key_strengths(personality_type, scores):

    """

    [HINGLISH]

    Use: Ye `views.py` me personality result page par dikhane ke liye use hota h.

    Why: User ko batane ke liye ki unki personality ke hisab se unki strengths kya hain.

    Effect: User ko confidence milta h aur wo apne career me in strengths ko use kar sakte h.

    """

    strengths_map = {

        'INTJ': ['Strategic Thinking', 'Analytical Mind', 'Independent Worker'],

        'ENTP': ['Innovative Thinking', 'Adaptability', 'Creative Problem Solving'],

        'INFP': ['Creativity', 'Empathy', 'Authenticity'],

        'ISTJ': ['Reliability', 'Attention to Detail', 'Practical Thinking']

    }

    return strengths_map.get(personality_type, ['Adaptability', 'Problem Solving', 'Learning Ability'])



def get_career_recommendations(personality_type, scores):

    """

    [HINGLISH]

    Use: Ye sirf `personality_result` page par quick suggestions ke liye use hota h.

    Why: Personality test ke turant baad kuch basic careers dikhane ke liye.

    Effect: User ko instant feedback milta h (Main matching dashboard par hoti h).

    """

    career_map = {

        'INTJ': [{'title': 'Data Scientist'}, {'title': 'Software Architect'}],

        'ENTP': [{'title': 'Entrepreneur'}, {'title': 'Product Manager'}],

        'INFP': [{'title': 'Graphic Designer'}, {'title': 'UX Designer'}],

        'ISTJ': [{'title': 'Financial Analyst'}, {'title': 'Systems Analyst'}]

    }

    return career_map.get(personality_type, [{'title': 'Business Analyst'}, {'title': 'Project Coordinator'}])





# --- CAREER RECOMMENDATION LOGIC ---



def generate_career_recommendations(profile):

    """

    [HINGLISH]

    Use: Ye `views.py` me dashboard load hone par call hota h.

    Why: Ye main function h jo ML models ko run karke best careers dhundhta h aur DB me save karta h.

    Effect: User ko dashboard par personalized career suggestions milte h.

    """

    

    # 1. Clear existing recommendations to avoid duplicates in DB

    CareerRecommendation.objects.filter(user_profile=profile).delete()



    # 2. Get matches using the enhanced ML function

    matches = enhanced_find_career_matches(profile)

    

    # FIXED: Fallback if no matches found (e.g. strict filtering returned nothing)

    if not matches:

        print("⚠️ No matches found with enhanced logic. Using fallback.")

        matches = enhanced_simple_match_fallback(profile, SkillAssessment.objects.filter(user_profile=profile))

    

    # 3. Save top 10 recommendations

    for match in matches[:10]:

        try:

            career_title = match['title']

            

            # --- DATA SYNC: Find full details from Global DataFrame (CAREER_DF) ---

            # This ensures we store Skills, Description, etc., not just the Title.

            career_data_row = {}

            if 'CAREER_DF' in globals() and not CAREER_DF.empty:

                # Find the row in CSV matching this title

                found_rows = CAREER_DF[CAREER_DF['career_name'] == career_title]

                if not found_rows.empty:

                    career_data_row = found_rows.iloc[0].to_dict()



            # Extract fields safely (handle missing data)

            description = match.get('description') or career_data_row.get('description', 'A highly recommended career path.')

            req_skills = career_data_row.get('required_skills', '')

            category = career_data_row.get('category', 'Technology') # Default if missing

            education = career_data_row.get('education_required', '')



            # --- DB UPDATE: Get or Create Career Object ---

            # FIXED: Provide defaults for mandatory fields to prevent IntegrityError on create

            # REMOVED: 'category' field as it does not exist in Career model

            defaults = {

                'description': description,

                'required_skills': req_skills,

                'education_required': education,
                
                'domain': career_data_row.get('domain', 'General'),

                'average_salary': float(career_data_row.get('average_salary', 50000.00) or 50000.00),

                'job_growth_rate': float(career_data_row.get('job_growth_rate', 0.05) or 0.05),

                'work_environment': 'Office/Remote', # Default

            }

            

            career_obj, created = Career.objects.get_or_create(

                title=career_title,

                defaults=defaults

            )



            if not created:

                # Update fields if object already exists

                career_obj.description = description

                if req_skills:

                    career_obj.required_skills = req_skills

                if education:

                    career_obj.education_required = education

                

                # Update stats if they are 0/default

                if not career_obj.average_salary:

                    career_obj.average_salary = defaults['average_salary']

                if not career_obj.job_growth_rate:

                    career_obj.job_growth_rate = defaults['job_growth_rate']

                

                career_obj.save()

            

            # --- CREATE RECOMMENDATION ENTRY ---

            CareerRecommendation.objects.create(

                user_profile=profile,

                recommended_career=career_obj,

                match_score=match['match_score'],

                reasoning=f"Match based on skills ({round(match.get('skills_match', 0), 1)}%), experience, and market fit."

            )

            

        except Exception as e:

            print(f"Error creating recommendation for {match.get('title', 'Unknown')}: {e}")

            continue



            print(f"Error creating recommendation for {match.get('title', 'Unknown')}: {e}")

            continue



class SkillWrapper:

    """Helper class to treat text-based skills same as DB objects"""

    def __init__(self, name, level='intermediate', years=0):

        self.skill_name = name

        self.skill_level = level

        self.years_of_experience = years



def get_combined_user_skills(profile):

    """

    Combines skills from SkillAssessment DB and profile.skills text.

    Returns a list of SkillWrapper-like objects.

    """

    # 1. Get DB skills

    db_skills = list(SkillAssessment.objects.filter(user_profile=profile))

    db_skill_names = {s.skill_name.lower() for s in db_skills}

    

    combined_skills = db_skills.copy()

    

    # 2. Get Text skills (from Resume/Profile)

    if profile.skills:

        # Use smart split or simple split

        text_skills = [s.strip() for s in profile.skills.split(',') if s.strip()]

        for s_name in text_skills:

            if s_name.lower() not in db_skill_names:

                # Add as wrapper object

                # Default to 'intermediate' and profile.experience_years

                combined_skills.append(SkillWrapper(

                    name=s_name, 

                    level='intermediate', 

                    years=profile.experience_years

                ))

                db_skill_names.add(s_name.lower())

                

    return combined_skills



def build_career_profile(career_row):

    """

    Constructs a text profile for a career from its data row.

    Used for vectorization and similarity matching.

    """

    # Combine relevant fields into a single string

    return f"{career_row.get('career_name', '')} {career_row.get('description', '')} {career_row.get('required_skills', '')} {career_row.get('education_required', '')}"



def compute_match_percentage(user_profile, career_obj, ml_score, user_skills):
    """
    Calculates the final match percentage with STRUCTURAL PENALTIES for mismatches.
    """
    # 1. Hard Skill Check
    req_skills = career_obj.required_skills
    
    is_tech_role = 'Technology' in career_obj.domain or 'Engineering' in career_obj.domain \
                   or 'Data' in career_obj.domain
                   
    # Count strict overlap (ignoring soft skills for tech roles)
    count, pct, missing = compute_skill_overlap(user_skills, req_skills, is_tech_role=is_tech_role)
    
    # CRITICAL: If overlap is too low for a technical role, drastically reduce score
    # REQUIREMENT: < 30% overlap -> REMOVE (We return low score here, filter later)
    if is_tech_role:
        if pct < 30.0:
            return 10.0 # Force fail
            
            
    # 2. ML Score (0-100) - WEIGHT: 25%
    # Amply high scores using square function to create separation
    normalized_ml = min(1.0, ml_score)
    amplified_ml = (normalized_ml ** 2) * 100
    weighted_ml = amplified_ml * 0.25

    # 3. Skills Match (0-100) - WEIGHT: 45% (Primary Factor)
    # We use the raw pct from above for scoring
    skills_score = min(100, pct)
    weighted_skills = skills_score * 0.45

    # 4. Experience Match (0-100) - WEIGHT: 10%
    total_exp = sum(s.years_of_experience for s in user_skills)
    exp_score = min(100, (total_exp / 10) * 100)
    weighted_exp = exp_score * 0.10

    # 5. Personality Match (0-100) - WEIGHT: 20%
    career_dict = {'career_name': career_obj.title}
    p_multiplier = calculate_personality_bonus(user_profile.personality_type, career_dict)
    
    if p_multiplier >= 1.20: p_score = 100
    elif p_multiplier >= 1.15: p_score = 90
    elif p_multiplier >= 1.10: p_score = 80
    elif p_multiplier > 1.0: p_score = 70
    else: p_score = 50
        
    weighted_personality = p_score * 0.20
    
    final_score = weighted_ml + weighted_skills + weighted_exp + weighted_personality
    return min(99.9, final_score)


def enhanced_find_career_matches(user_profile):
    """
    Core recommendation engine with STRICT DOMAIN LOCKING and HARD FILTERS.
    """
    profile = user_profile
    user_skills = get_combined_user_skills(profile)
    
    profile_text = f"{profile.skills} {profile.education_level} {getattr(profile, 'resume_text', '')}"
    
    # 1. STRICT DOMAIN LOCKING
    user_domain = detect_user_domain(profile_text, user_skills)
    print(f"DEBUG: User Locked to Domain: {user_domain.upper()}")
    
    # 2. Setup safe fallbacks based on domain
    safe_fallbacks = []
    if user_domain == 'medical':
        safe_fallbacks = ['General Physician', 'Clinical Research Associate', 'Healthcare Administrator', 'Public Health Specialist', 'Medical Officer', 'Nurse', 'Pharmacist']
    elif user_domain == 'legal':
        safe_fallbacks = ['Corporate Lawyer', 'Legal Associate', 'Paralegal', 'Legal Consultant']
    elif user_domain == 'finance':
        safe_fallbacks = ['Accountant', 'Financial Analyst', 'Tax Consultant', 'Auditor']
    
    # 3. ML Matching (Initial Broad Search)
    if not models_loaded:
        return enhanced_simple_match_fallback(profile, user_skills, user_domain, safe_fallbacks)
        
    user_skills_text = ' '.join([f"{skill.skill_name} " * (int(skill.years_of_experience) + 1) for skill in user_skills])
    ml_input = f"{user_domain} {user_skills_text} {profile.education_level}"
    
    user_vector = VECTORIZER.transform([ml_input])
    similarity_scores = cosine_similarity(user_vector, CAREER_VECTORS).flatten()
    ranked_indices = np.argsort(similarity_scores)[::-1]
    
    matches = []
    seen_titles = set()
    
    # We iterate until we find enough valid matches or run out
    for index in ranked_indices[:500]: 
        if index >= len(CAREER_DF): continue
        
        career_row = CAREER_DF.iloc[index]
        career_title = career_row['career_name']
        career_domain = str(career_row.get('domain', 'General')).lower()
        
        # --- FILTER 1: STRICT DOMAIN LOCK ---
        # If user is Medical/Legal/Finance, determine if career is allowed
        if user_domain in ['medical', 'legal', 'finance', 'defense', 'arts']:
            is_valid_domain = False
            if user_domain in career_domain: is_valid_domain = True
            
            # Allow General domain ONLY if it's not a Tech role masked as general
            if 'general' in career_domain:
                title_lower = career_title.lower()
                if not ('developer' in title_lower or 'engineer' in title_lower or 'scientist' in title_lower):
                    is_valid_domain = True
            
            # Special case: 'Healthcare' matches 'Medical'
            if user_domain == 'medical' and 'health' in career_domain:
                is_valid_domain = True

            if not is_valid_domain:
                continue

        # --- FILTER 2: TECH BARRIER ---
        # If user is NOT Engineering/Tech, reject typical Tech/Eng roles
        if user_domain != 'engineering':
            title_lower = career_title.lower()
            if 'developer' in title_lower or 'engineer' in title_lower or 'data scientist' in title_lower:
                continue

        clean_title = clean_title_for_merge(career_title)
        if clean_title in seen_titles: continue

        # Get/Create Object
        try:
            career_obj = Career.objects.get(title=career_title)
        except Career.DoesNotExist:
             class TempCareer:
                def __init__(self, title, req_skills, dom):
                    self.title = title
                    self.required_skills = req_skills
                    self.domain = dom
             career_obj = TempCareer(career_title, career_row.get('required_skills', ''), career_domain)

        # --- FILTER 3: HARD SKILL OVERLAP (CRITICAL) ---
        is_tech = 'Technology' in career_obj.domain or 'Engineering' in career_obj.domain or 'Data' in career_obj.domain or 'Science' in career_obj.domain
        
        # Calculate overlap IGNORING soft skills for tech roles
        count, pct, _ = compute_skill_overlap(user_skills, career_obj.required_skills, is_tech_role=is_tech)
        
        # MANDATORY REQUIREMENT: If overlap < 40%, REMOVE for tech roles
        if is_tech and pct < 40.0:
            continue 

        # Calculate Score
        ml_raw_score = similarity_scores[index]
        final_score = compute_match_percentage(profile, career_obj, ml_raw_score, user_skills)
        
        # STRICT PERSONALITY FILTER
        # If personality misalignment, penalize score
        p_bonus = calculate_personality_bonus(profile.personality_type, {'career_name': career_title})
        if p_bonus < 1.0:
             # Significant penalty for mismatch
             final_score -= 20.0
        
        # --- FILTER 4: CONFIDENCE THRESHOLD ---
        if final_score < 50.0:
            continue

        matches.append({
            'title': career_title,
            'match_score': round(final_score, 1),
            'description': career_row.get('description', ''),
            'skills_match': round(pct, 1)
        })
        seen_titles.add(clean_title)
        
        if len(matches) >= 10: break
        
    # --- FALLBACK IF NO MATCHES ---
    if not matches:
        print("⚠️ Strict filtering removed all ML matches. Using Safe Fallback.")
        return enhanced_simple_match_fallback(profile, user_skills, user_domain, safe_fallbacks)
        
    return matches



def calculate_skills_match_bonus(user_skills, career_obj):
    """
    Calculates skills match score (0-100).
    Using simple overlap percentage now.
    """
    if not user_skills: return 0
        
    # Get required skills string
    req_skills_str = ""
    if hasattr(career_obj, 'required_skills'):
        req_skills_str = career_obj.required_skills
    elif isinstance(career_obj, dict):
        req_skills_str = career_obj.get('required_skills', '')
        
    if not req_skills_str: return 0
        
    count, pct, _ = compute_skill_overlap(user_skills, req_skills_str)
    return min(100, pct)

    
def calculate_personality_bonus(personality_type, career):
    """
    [HINGLISH]
    Use: Ye `enhanced_find_career_matches` me use hota h.
    Why: Agar user ki personality job role se match karti h (e.g., Introvert -> Coder), to bonus milta h.
    Effect: User ko wo jobs milti h jisme wo khush rahenge.
    """
    if not personality_type or personality_type == 'Not assessed':
        return 1.0
    
    career_title = career['career_name'].lower()
    
    # Define primary personality alignments for different career categories
    type_career_map = {
        # Analytical, Strategic, Technical (INTx, ENTx, ISTJ)
        'tech_analyt': ['INTJ', 'INTP', 'ENTJ', 'ENTP', 'ISTJ'],
        # Creative, People-focused (INFx, ENFx, ISFP, ESFP)
        'creative_huma': ['INFJ', 'INFP', 'ENFJ', 'ENFP', 'ISFP', 'ESFP'],
        # Practical, Organized, Management (ESTJ, ISFJ, ISTP, ESTP)
        'admin_opera': ['ESTJ', 'ISFJ', 'ISTP', 'ESTP'],
        # Medical, Care (INFJ, ISFJ, ESFJ, ENFJ)
        'medical_care': ['INFJ', 'ISFJ', 'ESFJ', 'ENFJ', 'ISFP'],
        # Legal, Debate (ENTP, ESTJ, ENTJ, ISTJ)
        'legal_strat': ['ENTP', 'ESTJ', 'ENTJ', 'ISTJ', 'INTJ'],
    }
    
    # Define career category keywords
    career_keywords = {
        'tech_analyt': ['software', 'developer', 'engineer', 'data', 'ai', 'machine learning', 'cybersecurity', 'analyst', 'cloud'],
        'creative_huma': ['designer', 'writer', 'ux', 'ui', 'counselor', 'hr', 'marketing', 'product manager', 'artist'],
        'admin_opera': ['manager', 'finance', 'logistics', 'supervisor', 'admin', 'operations', 'project coordinator', 'business'],
        'medical_care': ['doctor', 'physician', 'nurse', 'surgeon', 'medical', 'clinical', 'therapist', 'health'],
        'legal_strat': ['lawyer', 'legal', 'advocate', 'attorney', 'judge', 'corporate law'],
    }
    
    # Determine career category
    career_category = 'none'
    for cat, keywords in career_keywords.items():
        if any(keyword in career_title for keyword in keywords):
            career_category = cat
            break
            
    # Apply bonus based on alignment (Max multiplier 1.20)
    if not career_category or career_category == 'none':
        return 1.0

    aligned_types = type_career_map.get(career_category, [])
    if personality_type in aligned_types:
        return 1.20 # Strong Match (Increased from 1.15)
        
    # Secondary/Partial Matches
    if career_category == 'tech_analyt' and personality_type in ['INFJ', 'ISTP']: # Logic + Intuition
        return 1.10
    if career_category == 'medical_care' and personality_type in ['INTJ', 'ISTJ']: # Precision
        return 1.10
        
    return 1.0



def enhanced_simple_match_fallback(profile, user_skills, user_domain='general', safe_fallbacks=None):
    """
    Fallback that respects domain safety.
    """
    matches = []
    
    # 1. If we have safe fallbacks for this domain, prioritize them
    if safe_fallbacks:
        print(f"DEBUG: Using Safe Fallbacks for {user_domain}: {safe_fallbacks}")
        for title in safe_fallbacks:
            # Find in DF to get desc
            desc = "Recommended based on your domain expertise."
            if 'CAREER_DF' in globals() and not CAREER_DF.empty:
                 row = CAREER_DF[CAREER_DF['career_name'] == title]
                 if not row.empty:
                    desc = row.iloc[0].get('description', desc)
            
            # --- DYNAMIC SCORING FOR FALLBACKS ---
            base_score = 60.0
            
            # 1. Personality Variance
            p_bonus = calculate_personality_bonus(profile.personality_type, {'career_name': title})
            if p_bonus >= 1.2: base_score += 8.0  # Strong personality match
            elif p_bonus >= 1.1: base_score += 5.0
            
            # 2. Skill Variance (Simple Overlap)
            # Try to get required skills from DB or DF (assuming services has access to helpers)
            # We don't want to query DB inside loop too heavily, but it is fine for < 10 items.
            try:
                c_obj = Career.objects.filter(title=title).first()
                if c_obj:
                     # Check skill match
                     count, pct, _ = compute_skill_overlap(user_skills, c_obj.required_skills)
                     if pct > 10: base_score += (pct * 0.2) # Add up to 20 points
            except:
                pass

            # 3. Random Jitter (Deterministic hash) to ensure not all look IDENTICAL
            jitter = (hash(title) % 50) / 10.0 # 0.0 to 5.0
            
            final_score = min(95.0, base_score + jitter)

            matches.append({
                'title': title,
                'match_score': round(final_score, 1),
                'description': desc,
                'skills_match': 50.0  # Placeholder, updated later if real object exists
            })
        return matches

    # 2. CHECK: Is this a "High Skill Entry Level" user?
    # Condition: 0-1 years exp AND > 3 tech skills
    skill_names = [s.skill_name.lower() for s in user_skills]
    tech_keywords = ['python', 'java', 'c++', 'sql', 'django', 'react', 'aws', 'machine learning', 'data']
    tech_skill_count = sum(1 for s in skill_names if any(k in s for k in tech_keywords))
    
    is_technical = 'medical' not in user_domain and 'legal' not in user_domain and 'finance' not in user_domain # Rough check
    
    # If explicitly technical domain OR distinct tech skills
    if (is_technical and tech_skill_count >= 3) or user_domain in ['engineering', 'technology']:
        print(f"DEBUG: Detected High Skill Entry Level User ({tech_skill_count} tech skills). Forcing Tech Roles.")
        
        # Override generic fallbacks with Entry-Level Tech Roles
        tech_fallbacks = [
            {'title': 'Junior Software Developer', 'desc': 'Entry-level development role.'},
            {'title': 'Junior Data Analyst', 'desc': 'Start your career in data analytics.'},
            {'title': 'Python Developer (Entry Level)', 'desc': 'Backend development with Python/Django.'},
            {'title': 'IT Support Specialist', 'desc': 'Technical support and systems administration.'},
            {'title': 'Web Developer Intern', 'desc': 'Frontend/Backend web development internship.'}
        ]
        
        for role in tech_fallbacks:
            matches.append({
                'title': role['title'],
                'match_score': 75.0, # Higher than generic
                'description': role['desc'],
                'skills_match': 80.0
            })
            
        return matches

    # 3. General Fallback DEPRECATED
    # STRICT MODE: No generic fallbacks allowed.
    # If we reached here, the user has no domain match and no tech match.
    # Return empty to prompt "No suitable career found".
    print("DEBUG: No strict matches found. Returning empty list.")
    return matches
def fetch_live_market_data(job_title):

    """

    Fetches real-time job market data using JSearch API (RapidAPI).

    Falls back to CSV data if API fails or key is missing.

    Results are cached for 24 hours to save quota.

    """

    clean_key = clean_title_for_merge(job_title)

    cache_key = f"market_data_{clean_key}"

    

    # 1. Check Cache

    cached_data = cache.get(cache_key)

    if cached_data:

        return cached_data



    # 2. Try API (if key exists)

    api_key = getattr(settings, 'RAPIDAPI_KEY', None)

    

    if api_key and api_key != 'YOUR_RAPIDAPI_KEY_HERE':

        try:

            url = "https://jsearch.p.rapidapi.com/search"

            querystring = {"query": f"{job_title} jobs in USA", "num_pages": "1"} # Defaulting to USA for broad data

            headers = {

                "X-RapidAPI-Key": api_key,

                "X-RapidAPI-Host": getattr(settings, 'RAPIDAPI_HOST', 'jsearch.p.rapidapi.com')

            }

            

            response = requests.get(url, headers=headers, timeout=5)

            

            if response.status_code == 200:

                data = response.json()

                jobs = data.get('data', [])

                

                if jobs:

                    # Calculate simple stats from the first page of results

                    salaries = []

                    for job in jobs:

                        # Extract salary if available (it"s often unstructured)

                        # This is a simplification; real parsing is complex

                        pass 

                        

                    # For now, JSearch mainly gives active job listings. 

                    # We can use the COUNT of jobs as a proxy for demand/growth

                    job_count = len(jobs)

                    

                    # Heuristic for growth/demand based on live job volume

                    growth_rate = 0.05

                    if job_count > 20: growth_rate = 0.15

                    elif job_count > 10: growth_rate = 0.08

                    

                    result = {

                        'job_growth_rate': growth_rate,

                        'demand_level': 'High' if job_count > 15 else 'Medium',

                        'source': 'Live API',

                        'job_count': job_count

                    }

                    

                    # Cache the result

                    cache.set(cache_key, result, timeout=86400) # 24 hours

                    return result

                    

        except Exception as e:

            print(f"API Fetch Error for {job_title}: {e}")



    # 3. Fallback removed (CSV deleted)

    return {

        'job_growth_rate': get_default_growth_by_title(job_title) / 100,

        'demand_level': generate_demand_level_by_title(job_title),

        'source': 'Heuristic'

    }



def enhance_recommendation_with_market_data(rec):

    """

    Attaches market data to a recommendation object using live data or fallback.

    """

    # Initialize default structure

    rec.market_data = {

        'job_growth_rate': 0.05,

        'demand_level': 'Medium',

        'salary_range': format_salary(rec.recommended_career.average_salary),

        'source': 'Default'

    }

    

    try:

        # Fetch data (Live -> CSV -> Heuristic)

        live_data = fetch_live_market_data(rec.recommended_career.title)

        

        # Update recommendation object temporary fields (not saving to DB to avoid thrashing)

        rec.market_data.update(live_data)

        

        # Format growth rate for display (e.g., 0.15 -> 15.0)

        rec.market_data['growth_percentage'] = round(rec.market_data['job_growth_rate'] * 100, 1)

        

        # If API returns salary (future implementation), update here. 

        # For now, keep DB salary but formatted

        

    except Exception as e:

        print(f"Error adhering market data: {e}")

        

    return rec

    from .models import Career

    

    # 1. Get Required Skills for Career

    required_skills_raw = ""

    

    # Try DB first

    career_obj = Career.objects.filter(title=target_career).first()

    if career_obj and career_obj.required_skills:

        required_skills_raw = career_obj.required_skills

    

    # Fallback to CSV

    if not required_skills_raw and 'CAREER_DF' in globals() and not CAREER_DF.empty:

        clean_target = clean_title_for_merge(target_career)

        career_rows = CAREER_DF[CAREER_DF['clean_key'] == clean_target]

        if not career_rows.empty:

            required_skills_raw = career_rows.iloc[0].get('required_skills', '')

            

    if not required_skills_raw:

        return {

            'gap_score': 0, 'missing_skills': [], 'required_skills': [], 

            'current_skills': [], 'coverage_percentage': 0

        }

        

    # 2. Parse Required Skills

    required_skills_list = smart_split_skills(str(required_skills_raw))

    required_skills_set = set([s.strip().lower() for s in required_skills_list if s.strip()])

    

    # 3. Parse User Skills

    user_skills_set = set()

    if user_skills:

        # user_skills can be a string or list

        if isinstance(user_skills, str):

            user_skills_list = [s.strip() for s in user_skills.split(',') if s.strip()]

            user_skills_set = set([s.lower() for s in user_skills_list])

        elif isinstance(user_skills, list):

            # Assuming list of SkillWrapper or similar

            user_skills_set = set([s.skill_name.lower() for s in user_skills])

            

    # 4. Calculate Intersection and Gap

    matching_skills = required_skills_set.intersection(user_skills_set)

    missing_skills = required_skills_set - user_skills_set

    

    required_count = len(required_skills_set)

    matching_count = len(matching_skills)

    

    coverage = (matching_count / required_count * 100) if required_count > 0 else 0

    gap_score = 1.0 - (matching_count / required_count) if required_count > 0 else 0

    

    # Format for display

    return {

        'required_skills': [{'name': s.title()} for s in required_skills_set],

        'current_skills': [{'name': s.title()} for s in matching_skills],

        'missing_skills': [{'name': s.title()} for s in missing_skills],

        'gap_score': round(gap_score, 2),

        'required_skills_count': required_count,

        'current_skills_count': matching_count,

        'missing_skills_count': len(missing_skills),

        'coverage_percentage': round(coverage, 1)

    }







def update_user_profile_skills(profile):

    """

    [HINGLISH]

    Use: Ye `views.py` me tab use hota h jab user koi naya skill add/delete karta h.

    Why: `SkillAssessment` table aur `UserProfile` table ko sync rakhne ke liye.

    Effect: Profile me hamesha latest skills ki list rehti h.

    """

    try:

        user_skills = SkillAssessment.objects.filter(user_profile=profile)

        skills_list = [skill.skill_name for skill in user_skills]

        profile.skills = ', '.join(skills_list)

        profile.save()

    except Exception as e:

        print(f"❌ Error updating profile skills: {e}")



def generate_skill_recommendations_based_on_profile(profile):

    """

    [HINGLISH]

    Use: Ye `views.py` me skills page par suggestions dikhane ke liye use hota h.

    Why: User ko batane ke liye ki wo aur kya seekh sakte h.

    Effect: User engagement badhta h aur wo naye skills add karte h.

    """

    try:

        current_skills = {skill.skill_name.lower() for skill in SkillAssessment.objects.filter(user_profile=profile)}

        

        # Get trending skills from dataset (using SKILLS_DF if available)

        trending_skills = []

        if SKILLS_DF is not None and not SKILLS_DF.empty and 'skill_name' in SKILLS_DF.columns:

            trending_skills = SKILLS_DF['skill_name'].tolist()

        

        # Fallback if no data or SKILLS_DF is missing

        if not trending_skills:

            trending_skills = [

                'Python', 'JavaScript', 'Machine Learning', 'Data Analysis', 

                'Cloud Computing', 'React', 'SQL', 'Project Management',

                'Communication', 'Problem Solving', 'Team Leadership'

            ]

        

        # Get career-based recommendations

        career_based_skills = generate_career_based_skill_recommendations(profile)

        

        # Combine and remove duplicates

        all_recommendations = list(set(trending_skills + career_based_skills))

        

        # Filter out skills user already has

        recommended_skills = []

        for skill in all_recommendations:

            if skill.lower() not in current_skills:

                recommended_skills.append(skill)

            if len(recommended_skills) >= 8: # Limit to 8 recommendations

                break

        

        return recommended_skills

    except Exception as e:

        print(f"Error generating skill recommendations: {e}")

        return ['Python', 'Data Analysis', 'Communication', 'Problem Solving']



def generate_career_based_skill_recommendations(profile):

    """

    [HINGLISH]

    Use: Ye `generate_skill_recommendations_based_on_profile` me use hota h.

    Why: User ke top careers ke hisab se skills suggest karne ke liye.

    Effect: Recommendations relevant hoti h, random nahi.

    """

    try:

        career_based_skills = []

        

        # Get user's top career matches

        top_careers = CareerRecommendation.objects.filter(

            user_profile=profile

        ).order_by('-match_score')[:3]

        

        for career_rec in top_careers:

            career = career_rec.recommended_career

            # Use smart_split_skills here if career.required_skills stores data with complex formatting

            required_skills = smart_split_skills(career.required_skills) if career.required_skills else []

            career_based_skills.extend([skill.strip() for skill in required_skills if skill.strip()])

        

        # Add skills based on personality type

        personality_skills = get_skills_by_personality(profile.personality_type)

        career_based_skills.extend(personality_skills)

        

        return list(set(career_based_skills)) 

    except Exception as e:

        print(f"Error generating career-based skills: {e}")

        return []



def fetch_youtube_resources(skill_name, domain='general', career_context='', max_results=3):
    """
    Fetches videos for a skill using YouTube Data API.
    Enforces strict domain blocking (e.g., No Tech for Medical).
    """
    # 1. STRICT BLOCKLIST FOR NON-TECH DOMAINS
    domain_lower = domain.lower()
    if domain_lower in ['medical', 'legal', 'finance', 'arts']:
        forbidden_keywords = ['python', 'java', 'aws', 'cloud', 'system design', 'react', 'node', 'c++', 'software', 'programming', 'coding', 'devops']
        if any(bad in skill_name.lower() for bad in forbidden_keywords):
            print(f"🚫 BLOCKED: Skipping forbidden tech skill '{skill_name}' for {domain} domain.")
            return []

    cache_key = f"yt_res_{skill_name}_{domain}_{max_results}"
    cached = cache.get(cache_key)
    if cached:
        return cached
        
    api_key = getattr(settings, 'YOUTUBE_API_KEY', None)
    # DEBUG: Check if key is loaded
    if not api_key or api_key == 'YOUR_YOUTUBE_API_KEY_HERE':
        print("DEBUG: YouTube API Key is MISSING or DEFAULT.")
        return []

    try:
        # 2. DOMAIN-SPECIFIC QUERY CONSTRUCTION
        query = f"{skill_name} tutorial for beginners"
        
        # Override query construction to be strictly career-focused
        if domain_lower == 'medical':
            query = f"{career_context or 'Doctor'} {skill_name} clinical training"
        elif domain_lower == 'legal':
            query = f"{career_context or 'Lawyer'} {skill_name} legal course"

        elif domain_lower != 'general' and career_context:
            query = f"{career_context} {skill_name} training"
            
        print(f"DEBUG: YouTube Query -> '{query}' (Domain: {domain_lower})")

        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            'part': 'snippet',
            'q': query,
            'type': 'video',
            'maxResults': max_results,
            'key': api_key
        }
        
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            print(f"DEBUG: YouTube API returned {len(items)} raw results.")
            
            resources = []
            for item in items:
                if 'videoId' not in item['id']: continue
                
                video_id = item['id']['videoId']
                snippet = item['snippet']
                title = snippet['title']
                
                # 3. POST-FETCH SAFETY FILTER (POSITIVE & NEGATIVE)
                title_lower = title.lower()
                desc_lower = snippet.get('description', '').lower()
                full_text = title_lower + " " + desc_lower
                
                if domain_lower == 'medical':
                    # Negative Filter (Block Tech)
                    forbidden_keywords = ['python', 'java', 'aws', 'cloud', 'system design', 'react', 'software', 'engineering', 'devops']
                    if any(bad in full_text for bad in forbidden_keywords):
                        print(f"DEBUG: Blocked '{title}' (Medical Negative Filter)")
                        continue
                        
                    # Positive Filter (Require Medical Context OR Skill Name)
                    # We relax this to allow the SKILL itself to be the validator.
                    required_medical_keywords = ['medical', 'clinical', 'health', 'doctor', 'patient', 'surgery', 'anatomy', 'medicine', 'hospital', 'nurse', 'physician', 'healthcare']
                    
                    # Split skill name into tokens (e.g. "Patient Diagnosis" -> "patient", "diagnosis")
                    skill_tokens = [s.lower() for s in skill_name.split()]
                    required_medical_keywords.extend(skill_tokens)
                    
                    if not any(good in full_text for good in required_medical_keywords):
                        print(f"DEBUG: Blocked '{title}' (Medical Positive Filter - Mismatch)")
                        # If the title matches NOTHING relevant, reject it
                        continue

                elif domain_lower == 'legal':
                    forbidden_keywords = ['python', 'java', 'aws', 'cloud', 'system design', 'react', 'software']
                    if any(bad in full_text for bad in forbidden_keywords):
                        print(f"DEBUG: Blocked '{title}' (Legal Negative Filter)")
                        continue

                resources.append({
                    'title': title,
                    'channel': snippet['channelTitle'],
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'thumbnail': snippet['thumbnails']['high']['url']
                })
            
            if resources:
                cache.set(cache_key, resources, timeout=86400 * 3) # Cache for 3 days
                return resources
                
    except Exception as e:
        print(f"YouTube API Error for {skill_name}: {e}")
        
    return []



def get_learning_resources(profile):
    """
    [HINGLISH]
    Use: Ye `views.py` me Learning Hub page par resources dikhane ke liye use hota h.
    Why: User ke target career aur missing skills ke hisab se curated content lane ke liye.
    Effect: User ko personalized roadmap aur videos milte h.
    """
    from .models import CareerRoadmap, LearningResource
    from .utils import normalize_skill
    
    # 1. Determine Target Career (Top Recommendation)
    target_career = "Software Engineer" # Default
    target_domain = "general"
    
    recommendation = CareerRecommendation.objects.filter(user_profile=profile).order_by('-match_score').first()
    
    if recommendation:
        target_career = recommendation.recommended_career.title
        # Fetch domain from related Career object
        target_domain = getattr(recommendation.recommended_career, 'domain', 'general') or 'general'
        
    # 2. Get Roadmap (Dynamic from DB)
    roadmap_steps = CareerRoadmap.objects.filter(career__title=target_career).order_by('step_number')
    
    if not roadmap_steps.exists():
        generate_dynamic_roadmap(target_career)
        roadmap_steps = CareerRoadmap.objects.filter(career__title=target_career).order_by('step_number')
        
    roadmap = []
    if roadmap_steps.exists():
        for step in roadmap_steps:
            roadmap.append({
                'step': step.step_number,
                'title': step.title,
                'desc': step.description
            })

    # 3. Identify Missing Skills (Gap Analysis)
    user_skills_objs = SkillAssessment.objects.filter(user_profile=profile)
    user_skills_list = [s.skill_name for s in user_skills_objs]
    if profile.skills:
        user_skills_list.extend([s.strip() for s in profile.skills.split(',') if s.strip()])
    user_skills_str = ", ".join(list(set(user_skills_list)))
    
    gap_data = predict_skill_gaps(user_skills_str, target_career)
    missing_skills = gap_data.get('missing_skills', [])
    
    # 4. Fetch Resources for Missing Skills (Dynamic from DB)
    video_resources = []
    course_resources = []
    
    # If no missing skills (perfect match), show advanced topics based on DOMAIN
    skills_to_learn = [s['name'] for s in missing_skills]
    
    if not skills_to_learn:
        dom_lower = target_domain.lower()
        if dom_lower == 'medical':
            skills_to_learn = ['Medical Ethics', 'Advanced Patient Care', 'Clinical Research']
        elif dom_lower == 'legal':
            skills_to_learn = ['Legal Research', 'Corporate Law', 'Case Analysis']
        elif dom_lower == 'finance':
            skills_to_learn = ['Financial Modeling', 'Risk Management', 'Regulatory Compliance']
        elif dom_lower == 'arts':
            skills_to_learn = ['Creative Portfolio', 'Design Trends', 'Art History']
        else:
            # Default for Tech/General
            skills_to_learn = ['System Design', 'Cloud Computing', 'Leadership']
        
    for skill in skills_to_learn:
        norm_skill = normalize_skill(skill)
        
        # A. Try DB First
        db_resources = LearningResource.objects.filter(skill_tag__iexact=norm_skill)
        
        # VALIDATE DB RESOURCES (Strict Domain Check)
        valid_db_resources = []
        if db_resources.exists():
            for res in db_resources:
                # Apply same strict logic to DB records
                title_lower = res.title.lower()
                dom_lower = target_domain.lower()
                
                is_valid = True
                if dom_lower == 'medical':
                    # Negative Filter
                    forbidden = ['python', 'java', 'aws', 'cloud', 'system design', 'react', 'software', 'engineering']
                    if any(bad in title_lower for bad in forbidden):
                        is_valid = False
                    
                    # Positive Filter (Must be medical)
                    required = ['medical', 'clinical', 'health', 'doctor', 'patient', 'surgery', 'anatomy', 'medicine']
                    # Check title only for DB as we might not have description
                    if not any(good in title_lower for good in required):
                        # Start strict: if title doesn't say medical, reject it.
                        is_valid = False
                        
                elif dom_lower == 'legal':
                    forbidden = ['python', 'java', 'aws', 'cloud', 'react']
                    if any(bad in title_lower for bad in forbidden):
                        is_valid = False
                        
                if is_valid:
                    valid_db_resources.append(res)
                else:
                    # Optional: Delete invalid resource to clean DB? 
                    # Only do this if we are sure it's not valid for ANYONE. 
                    # But resources are shared... Python is valid for Tech users.
                    # So we just don't include it for THIS user.
                    pass
        
        # B. If no VALID DB resources, Try API
        if not valid_db_resources:
            # Pass DOMAIN and CAREER context to ensure strict filtering
            api_videos = fetch_youtube_resources(skill, domain=target_domain, career_context=target_career)
            
            if api_videos:
                for vid in api_videos:
                    # Create new, potentially domain-specific resources
                    # Note: You might want to include domain in LearningResource model or skill_tag?
                    # For now, just adding them.
                     LearningResource.objects.get_or_create(
                        url=vid['url'],
                        defaults={
                            'title': vid['title'],
                            'resource_type': 'video',
                            'platform': vid['channel'],
                            'skill_tag': norm_skill,
                            'thumbnail_url': vid['thumbnail']
                        }
                    )
                # Refetch to include new ones
                db_resources = LearningResource.objects.filter(skill_tag__iexact=norm_skill)
                # We need to filter the NEWLY fetched ones too (though API should provide valid ones)
                valid_db_resources = [r for r in db_resources if r.url in [v['url'] for v in api_videos]]
            
        for res in valid_db_resources:
            if res.resource_type == 'video':
                video_resources.append({
                    'skill': skill,
                    'title': res.title,
                    'channel': res.platform,
                    'url': res.url,
                    'thumbnail': res.thumbnail_url or f"https://img.youtube.com/vi/{res.url.split('v=')[-1]}/mqdefault.jpg"
                })
            elif res.resource_type == 'course':
                course_resources.append({
                    'skill': skill,
                    'title': res.title,
                    'platform': res.platform,
                    'url': res.url
                })

    return {
        'target_career': target_career,
        'roadmap': roadmap,
        'videos': video_resources[:6], 
        'courses': course_resources[:4] 
    }



def generate_dynamic_roadmap(career_title):

    """

    Generates a roadmap for a career if it doesn't exist in DB.

    Uses static templates or keyword-based logic.

    """

    from .models import Career, CareerRoadmap

    

    try:

        # Find the career object

        career_obj = Career.objects.filter(title=career_title).first()

        if not career_obj:

            # Should exist if recommended, but safety check

            return



        # 1. Check Static Templates (REMOVED)

        template = None

        

        # 2. If no template, use Keyword Logic

        if not template:

            title_lower = career_title.lower()

            if 'manager' in title_lower or 'lead' in title_lower:

                template = [

                    {'step': 1, 'title': 'Core Competencies', 'desc': 'Master the fundamentals of the domain.'},

                    {'step': 2, 'title': 'Project Management', 'desc': 'Learn Agile, Scrum, and resource management.'},

                    {'step': 3, 'title': 'Team Leadership', 'desc': 'Develop soft skills, conflict resolution, and mentoring.'},

                    {'step': 4, 'title': 'Strategic Planning', 'desc': 'Understand business goals and long-term strategy.'},

                    {'step': 5, 'title': 'Advanced Certification', 'desc': 'PMP, MBA, or specialized leadership certs.'}

                ]

            elif 'designer' in title_lower:

                 template = [

                    {'step': 1, 'title': 'Design Fundamentals', 'desc': 'Color theory, typography, and layout.'},

                    {'step': 2, 'title': 'Tools Mastery', 'desc': 'Figma, Adobe XD, Photoshop, Illustrator.'},

                    {'step': 3, 'title': 'UX Principles', 'desc': 'User research, wireframing, and prototyping.'},

                    {'step': 4, 'title': 'Portfolio Building', 'desc': 'Create real-world projects to showcase skills.'},

                    {'step': 5, 'title': 'Specialization', 'desc': 'Motion design, 3D, or interaction design.'}

                ]

            else:

                # Generic Technical/Professional Fallback

                template = [

                    {'step': 1, 'title': 'Foundations', 'desc': f'Learn the basic principles of {career_title}.'},

                    {'step': 2, 'title': 'Core Tools', 'desc': 'Master the essential software and tools used in the industry.'},

                    {'step': 3, 'title': 'Advanced Concepts', 'desc': 'Deep dive into complex topics and methodologies.'},

                    {'step': 4, 'title': 'Practical Application', 'desc': 'Build projects or gain internship experience.'},

                    {'step': 5, 'title': 'Professional Development', 'desc': 'Networking, resume building, and interview prep.'}

                ]



        # 3. Save to DB

        for step in template:

            CareerRoadmap.objects.create(

                career=career_obj,

                step_number=step['step'],

                title=step['title'],

                description=step['desc']

            )

            

    except Exception as e:

        print(f"Error generating roadmap for {career_title}: {e}")







def calculate_profile_completion(profile):

    """

    [HINGLISH]

    Use: Ye `views.py` me dashboard par progress bar dikhane ke liye use hota h.

    Why: User ko motivate karne ke liye ki wo apna profile pura bhare.

    Effect: Gamification add hota h aur data quality improve hoti h.

    """

    completion = 0

    fields_to_check = [

        ('age', 15), ('gender', 15), ('education_level', 15), 

        ('skills', 20), ('personality_type', 15), ('resume_file', 20)

    ]



    for field, percentage in fields_to_check:

        if getattr(profile, field, None) and getattr(profile, field, None) not in ['', 'Not assessed']:

            completion += percentage

    return min(completion, 100)



def generate_personalized_insights(profile):

    """

    [HINGLISH]

    Use: Ye `views.py` me dashboard par personalized messages dikhane ke liye use hota h.

    Why: Dashboard ko static ki jagah dynamic aur personal feel dene ke liye.

    Effect: User ko lagta h ki system unhe samajhta h.

    """

    insights = []



    if profile.experience_years and profile.experience_years >= 5:

        insights.append(f"With {profile.experience_years} years of experience, you're well-positioned for senior roles.")



    # Count skills by words/tokens, not by raw characters

    skills_count = 0

    if profile.skills:

        tokens = [s.strip() for s in re.split(r'[;,\n]', profile.skills) if s.strip()]

        skills_count = len(tokens)

        if skills_count >= 8:

            insights.append(f"You have a strong skill set with {skills_count} documented skills.")

        elif skills_count <= 3:

            insights.append("Consider adding more skills to enhance your career opportunities.")



    if profile.personality_type and profile.personality_type != 'Not assessed':

        insights.append(f"Your {profile.personality_type} personality suggests strengths in creative problem-solving.")



    if not insights:

        insights.append("Complete your profile to get personalized career insights.")



    return insights

def predict_skill_gaps(user_skills_str, target_career):

    """

    [HINGLISH]

    Use: Gap analysis between user skills and career requirements.

    """

    from .models import Career

    from .utils import smart_split_skills, clean_title_for_merge

    

    # 1. Get Required Skills for Career

    required_skills_raw = ""

    

    # Try DB first

    career_obj = Career.objects.filter(title=target_career).first()

    if career_obj and career_obj.required_skills:

        required_skills_raw = career_obj.required_skills

    

    # Fallback to CSV (using CAREER_DF)

    if not required_skills_raw and 'CAREER_DF' in globals() and not CAREER_DF.empty:

        clean_target = clean_title_for_merge(target_career)

        career_rows = CAREER_DF[CAREER_DF['clean_key'] == clean_target]

        if not career_rows.empty:

            required_skills_raw = career_rows.iloc[0].get('required_skills', '')

            

    if not required_skills_raw:

        return {

            'gap_score': 0, 'missing_skills': [], 'required_skills': [], 

            'current_skills': [], 'coverage_percentage': 0

        }

        

    # 2. Parse Required Skills

    required_skills_list = smart_split_skills(str(required_skills_raw))

    required_skills_set = set([s.strip().lower() for s in required_skills_list if s.strip()])

    

    # 3. Parse User Skills

    user_skills_set = set()

    if user_skills_str:

        user_skills_list = [s.strip() for s in user_skills_str.split(',') if s.strip()]

        user_skills_set = set([s.lower() for s in user_skills_list])

            

    # 4. Calculate Intersection and Gap

    matching_skills = required_skills_set.intersection(user_skills_set)

    missing_skills = required_skills_set - user_skills_set

    

    required_count = len(required_skills_set)

    matching_count = len(matching_skills)

    

    coverage = (matching_count / required_count * 100) if required_count > 0 else 0

    gap_score = 1.0 - (matching_count / required_count) if required_count > 0 else 0

    

    # Format for display

    return {

        'required_skills': [{'name': s.title()} for s in required_skills_set],

        'current_skills': [{'name': s.title()} for s in matching_skills],

        'missing_skills': [{'name': s.title()} for s in missing_skills],

        'gap_score': round(gap_score, 2),

        'required_skills_count': required_count,

        'current_skills_count': matching_count,

        'missing_skills_count': len(missing_skills),

        'coverage_percentage': round(coverage, 1)
    }

# --- TRENDING JOBS LOGIC ---

def get_trending_jobs(domain, user_profile=None):
    """
    Fetches active Trending Jobs, prioritizing those matching the user's specific interests if possible.
    """
    # Base Query: Active jobs only
    query = TrendingJob.objects.filter(status='ACTIVE')
    
    # Domain Filter (Strict or Expanded)
    if domain and domain != 'General':
        # exact match
        query = query.filter(domain__icontains=domain)
        
    # Sort by Score (High to Low)
    trending_list = query.order_by('-trend_score')[:5]  # Top 5
    
    # Format for Template
    results = []
    for job in trending_list:
        results.append({
            'title': job.job_title,
            'source': job.source,
            'reason': job.trend_reason,
            'skills': job.required_skills,
            'industry': job.get_industry_type_display(),
            'score': job.trend_score
        })
        
    return results

# --- SKILL GAP ANALYSIS LOGIC ---

def analyze_skill_gap(user_profile, career_obj):
    """
    Compares User Skills vs Career Required Skills.
    Returns quantitative and qualitative gap analysis.
    """
    # 1. Get User Skills (Clean List)
    user_skill_assessments = SkillAssessment.objects.filter(user_profile=user_profile)
    user_skills = set([s.skill_name.lower().strip() for s in user_skill_assessments])
    
    # Add Resume Skills if available (merged in profile text fields usually, but let's be safe)
    if user_profile.skills:
        resume_skills = [s.strip().lower() for s in user_profile.skills.split(',')]
        user_skills.update(resume_skills)

    # 2. Get Career Skills
    required_raw = career_obj.required_skills
    required_skills = set([s.strip().lower() for s in required_raw.split(',') if s.strip()])
    
    # 3. Calculate Gaps
    # Intersection = Skills You Have
    have_skills = user_skills.intersection(required_skills)
    
    # Difference = Skills You Need
    missing_skills = required_skills - user_skills
    
    # 4. Score
    total_req = len(required_skills)
    if total_req > 0:
        match_percentage = (len(have_skills) / total_req) * 100
    else:
        match_percentage = 100 # No skills required?
        
    # 5. Resource Recommendations (Simple Link)
    # logic to get links specific to missing skills could go here
    
    return {
        'match_percentage': round(match_percentage, 1),
        'have_count': len(have_skills),
        'missing_count': len(missing_skills),
        'have_list': [s.title() for s in have_skills],
        'missing_list': [s.title() for s in missing_skills],
        'status': 'Ready' if match_percentage > 80 else 'Needs Work'
    }
