# Career Database Expansion Plan: "Project Sarvagya" (All-Knowing)

## 1. Executive Summary
This document outlines the strategy to transform the "AI Career Recommender" from a Data-Science-heavy tool into a **Comprehensive Career Guidance System** for the Indian context. 

**Current State:** 130,000+ entries skewed towards 8 Data/AI domains.
**Target State:** Balanced representation of 20+ major domains covering Engineering, Medical, Arts, Commerce, Government, and Vocational paths.

---

## 2. The Balancing Strategy (Critical)
**Problem:** Simply adding 100-500 new manually curated rows will not work because the existing 131,000 rows will statistically drown out the new data during AI training.

**Solution: Stratified Dataset Construction**
We will NOT just append data. We will create a `training_dataset.csv` that is composed of:
1.  **The New Manual Data:** 100% of the new curated entries.
2.  **The Existing Data (Downsampled):** detailed random sampling of the existing 130k rows, capped at ~500 entries per existing domain. 

This ensures the AI sees "Medical" and "Data Science" as equally important classes.

---

## 3. Standardized Data Schema (CSV Structure)
All new data must follow this schema to map correctly to your `Career` model and `train_models.py`.

| Column Header | Description | Example (Medical) | Example (Engineering) |
| :--- | :--- | :--- | :--- |
| `domain` | The Broad Category | Medical & Healthcare | Engineering & Technology |
| `career_name` | Specific Role Title | General Physician (MBBS) | Civil Engineer (Structural) |
| `description` | Role description & scope | Diagnoses and treats common diseases. Works in hospitals or clinics. | Designs and oversees construction of infrastructure like bridges and roads. |
| `required_skills` | Comma-separated skills | Diagnosis, Patient Care, Anatomy, Pharmacology, Empathy | AutoCAD, Structural Analysis, Concrete Tech, Project Management |
| `education_required`| Degree/Exam (India) | MBBS, NEET-UG, Internship | B.Tech/B.E. (Civil), JEE Main, GATE |
| `challenges` | Entry barriers/difficulty | High competition (NEET), Long study duration | Site work, Licensing requirements |
| `average_salary` | India-specific (Start-Mid) | ₹6,00,000 - ₹12,00,000 | ₹4,00,000 - ₹8,00,000 |
| `growth_rate` | Future details | High demand due to population | Steady demand in infrastructure |
| `job_role` | Entry Level Designation | Junior Resident / Medical Officer | Site Engineer / GET |

---

## 4. Comprehensive Domain Taxonomy (India-Specific)

### A. Engineering & Technology (Non-IT Core)
*   **Mechanical & Auto:** Automobile Engineer, Robotics Engineer, HVAC Specialist.
*   **Civil & Architecture:** Structural Engineer, Architect, Urban Planner.
*   **Electrical & Electronics:** Embedded Systems Engineer, Telecom Engineer, VLSI Designer.
*   **Specialized:** Aerospace Engineer, Biotech Engineer, Chemical Engineer.

### B. Medical & Healthcare
*   **Core Medical:** MBBS Doctor, Dentist (BDS), Surgeon, Psychiatrist.
*   **AYUSH:** Ayurvedic Doctor (BAMS), Homeopath (BHMS).
*   **Allied Health:** Physiotherapist, Pharmacist, Medical Lab Tech, Nurse, Nutritionist.

### C. Commerce, Finance & Management
*   **Accounting:** Chartered Accountant (CA), Company Secretary (CS), CMA.
*   **Finance:** Investment Banker, Stock Analyst, Actuary.
*   **Management:** MBA (HR/Marketing/Ops), Hotel Management, Event Management.

### D. Arts, Humanities & Law
*   **Law:** Corporate Lawyer, Judge/Magistrate, Criminal Lawyer (LLB/LLM).
*   **Social Sciences:** Psychologist, Sociologist, MSW (Social Worker).
*   **Liberal Arts:** Historian, Political Analyst, Archeologist.

### E. Media, Communication & Design
*   **Design:** Graphic Designer, UX/UI (Non-code), Fashion Designer, Interior Designer.
*   **Media:** Journalist, News Anchor, Content Writer, Video Editor, PR Specialist.

### F. Government & Defense (The "Sarkari" Sector)
*   **Civil Services:** IAS Officer, IPS Officer, IFS Officer.
*   **Banking & PSU:** PO (Bank), RBI Grade B, PSU Engineer (GATE).
*   **Defense:** NDA (Army/Navy/Air Force), CDS Officer, AFCAT.

### G. Emerging & Vocational
*   **Digital:** Digital Marketer, SEO Specialist, YouTuber/Influencer.
*   **Vocational:** Pilot, Merchant Navy, Chef, Air Hostess/Cabin Crew.
*   **Agriculture:** Agri-Business Manager, Soil 
Scientist.

---

## 5. Implementation Steps
1.  **Generate Data:** Use the provided `expanded_career_data.csv` (I will create this for you).
2.  **Update Loader:** Modify `train_models.py` to implement the "Stratified Sampling" logic.
3.  **Retrain:** Run the training script to regenerate the models.
4.  **Verify:** Test with non-tech inputs (e.g., "I like biology and helping people") to see if "Doctor" or "Nurse" appears.
