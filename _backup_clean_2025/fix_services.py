
import os
import re

# Define the new function code
NEW_FUNCTION_CODE = '''def enhanced_simple_match_fallback(profile, user_skills, user_domain='general', safe_fallbacks=None):
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
                
            matches.append({
                'title': title,
                'match_score': 60.0,
                'description': desc,
                'skills_match': 50.0 
            })
        return matches

    # 2. General Fallback (Only use Generic roles, never Tech)
    print("DEBUG: Using General Fallback")
    
    generic_roles = ['Administrative Assistant', 'Customer Service Representative', 'Sales Associate', 'Office Manager', 'Operations Coordinator']
    
    for title in generic_roles:
         matches.append({
            'title': title,
            'match_score': 55.0,
            'description': 'A versatile role suitable for various skill sets.',
            'skills_match': 40.0
        })
            
    return matches
'''

file_path = r"c:\Users\Nitin\Downloads\minor project BY ASUS_VIVOBOOK\minor project BY ASUS_VIVOBOOK\minor project\AI_Career_Recommender\ai_recommender\services.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Debug: Print a snippet of what we are looking for
start_marker = "def enhanced_simple_match_fallback(profile, user_skills):"
if start_marker not in content:
    print("CRITICAL ERROR: Start marker not found!")
    # Try to find it with spacing?
    match = re.search(r"def\s+enhanced_simple_match_fallback\s*\(", content)
    if match:
        print(f"Found fuzzy match at: {match.start()}")
    else:
        print("Fuzzy match also failed.")
        exit(1)

# Regex to capture the function
# We rely on the next function start 'def fetch_live_market_data' to end the capture
pattern = r"def enhanced_simple_match_fallback\(profile, user_skills\):.*?return sorted\(matches, key=lambda x: x\['match_score'\], reverse=True\)\[:10\]"

# Note: The original code has massive whitespace, so we need DOTALL
# And we need to be careful about the end.
# A safer way might be to split the file, find the start line, and find the end line.

lines = content.splitlines()
start_index = -1
end_index = -1

for i, line in enumerate(lines):
    if "def enhanced_simple_match_fallback(profile, user_skills):" in line:
        start_index = i
    if "def fetch_live_market_data(job_title):" in line:
        end_index = i
        break # The function ends before the next function starts

if start_index != -1 and end_index != -1:
    print(f"Locating function at lines {start_index+1} to {end_index}")
    
    # We replace from start_index to end_index - 1 (leaving blank lines before next function)
    # The new code needs to be split into lines
    new_lines = NEW_FUNCTION_CODE.splitlines()
    
    # Construct new file content
    final_lines = lines[:start_index] + new_lines + lines[end_index:]
    
    new_content = "\n".join(final_lines)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    print("Successfully replaced function!")

else:
    print(f"Failed to find boundaries. Start: {start_index}, End: {end_index}")
    # Try Regex fallback
    print("Attempting Regex fallback...")
    regex_pattern = r"(def enhanced_simple_match_fallback\(profile, user_skills\):.*?)(\s*def fetch_live_market_data)"
    
    replacement = NEW_FUNCTION_CODE + "\n\n\\2"
    
    new_content_re, count = re.subn(regex_pattern, replacement, content, flags=re.DOTALL)
    
    if count > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content_re)
        print("Successfully replaced using Regex!")
    else:
        print("Regex failed too.")

