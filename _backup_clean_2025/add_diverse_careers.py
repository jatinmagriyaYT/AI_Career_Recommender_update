import os
import django
import sys

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'AI_Career_Recommender.settings')
django.setup()

from ai_recommender.models import Career

def add_diverse_careers():
    careers_data = [
        # --- HEALTHCARE ---
        {
            'title': 'General Practitioner (Doctor)',
            'description': 'Diagnose and treat common health problems. Provide medical care to patients.',
            'required_skills': 'Medicine, Patient Care, Diagnostics, Anatomy, Physiology, Clinical Research, Communication',
            'average_salary': '150000',
            'job_growth_rate': 0.04,
            'education_required': 'MBBS / MD',
            'domain': 'Healthcare'
        },
        {
            'title': 'Surgeon',
            'description': 'Perform surgical procedures to treat injuries and diseases.',
            'required_skills': 'Surgery, Anatomy, Precision, Patient Safety, Medical Terminology, Critical Thinking',
            'average_salary': '250000',
            'job_growth_rate': 0.03,
            'education_required': 'MS / MD (Surgery)',
            'domain': 'Healthcare'
        },
        {
            'title': 'Registered Nurse',
            'description': 'Provide patient care, administer medication, and assist doctors.',
            'required_skills': 'Nursing, Patient Care, First Aid, Pharmacology, Empathy, Health Monitoring',
            'average_salary': '75000',
            'job_growth_rate': 0.06,
            'education_required': 'B.Sc Nursing',
            'domain': 'Healthcare'
        },
        
        # --- FINANCE ---
        {
            'title': 'Accountant',
            'description': 'Prepare and examine financial records. Ensure accuracy and compliance.',
            'required_skills': 'Accounting, Financial Analysis, Tax, Auditing, Excel, Budgeting, QuickBooks',
            'average_salary': '70000',
            'job_growth_rate': 0.04,
            'education_required': 'B.Com / CA / CPA',
            'domain': 'Finance'
        },
        {
            'title': 'Financial Analyst',
            'description': 'Analyze financial data to help businesses make investment decisions.',
            'required_skills': 'Financial Analysis, Data Analysis, Forecasting, Excel, Risk Management, Economics',
            'average_salary': '85000',
            'job_growth_rate': 0.05,
            'education_required': 'MBA Finance / CFA',
            'domain': 'Finance'
        },

        # --- ENGINEERING (Non-CS) ---
        {
            'title': 'Mechanical Engineer',
            'description': 'Design, develop, and test mechanical devices and sensors.',
            'required_skills': 'Mechanical Design, CAD, SolidWorks, Thermodynamics, Fluid Mechanics, Manufacturing',
            'average_salary': '85000',
            'job_growth_rate': 0.04,
            'education_required': 'B.Tech Mechanical',
            'domain': 'Engineering'
        },
        {
            'title': 'Civil Engineer',
            'description': 'Design and supervise construction projects like roads, buildings, and bridges.',
            'required_skills': 'Civil Engineering, AutoCAD, Structural Analysis, Project Management, Surveying, Concrete Technology',
            'average_salary': '82000',
            'job_growth_rate': 0.03,
            'education_required': 'B.Tech Civil',
            'domain': 'Engineering'
        },

        # --- MARKETING & SALES ---
        {
            'title': 'Digital Marketer',
            'description': 'Promote products and services through digital channels.',
            'required_skills': 'SEO, Content Marketing, Social Media Marketing, Google Analytics, Email Marketing, SEM',
            'average_salary': '65000',
            'job_growth_rate': 0.10,
            'education_required': 'BBA / Marketing Certification',
            'domain': 'Marketing'
        },
        {
            'title': 'Sales Manager',
            'description': 'Lead sales teams and develop sales strategies to hit targets.',
            'required_skills': 'Sales Strategy, Negotiation, CRM, Leadership, Communication, Market Analysis',
            'average_salary': '90000',
            'job_growth_rate': 0.05,
            'education_required': 'MBA / BBA',
            'domain': 'Sales'
        },

        # --- LEGAL ---
        {
            'title': 'Corporate Lawyer',
            'description': 'Advise corporations on their legal rights and obligations.',
            'required_skills': 'Corporate Law, Litigation, Legal Research, Contract Notation, Compliance, Critical Thinking',
            'average_salary': '120000',
            'job_growth_rate': 0.04,
            'education_required': 'LLB / LLM',
            'domain': 'Legal'
        },

        # --- CREATIVE ---
        {
            'title': 'Graphic Designer',
            'description': 'Create visual concepts to communicate ideas that inspire, inform, or captivate consumers.',
            'required_skills': 'Graphic Design, Photoshop, Illustrator, InDesign, Creativity, Typography, Branding',
            'average_salary': '55000',
            'job_growth_rate': 0.03,
            'education_required': 'B.Des / Diploma',
            'domain': 'Creative'
        }
    ]

    print(f"Adding/Updating {len(careers_data)} diverse careers...")

    for data in careers_data:
        career, created = Career.objects.get_or_create(
            title=data['title'],
            defaults={
                'description': data['description'],
                'required_skills': data['required_skills'],
                'average_salary': data['average_salary'],
                'job_growth_rate': data['job_growth_rate'],
                'education_required': data['education_required'],
                'domain': data['domain']
            }
        )
        
        if not created:
            # Update existing if needed (optional)
            career.description = data['description']
            career.required_skills = data['required_skills'] # Force update skills to match our new parser
            career.domain = data['domain']
            career.save()
            print(f"Updated: {career.title}")
        else:
            print(f"Created: {career.title}")

if __name__ == '__main__':
    add_diverse_careers()
