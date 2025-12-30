import pandas as pd
import numpy as np
import os

def balance_datasets():
    print("Project Sarvagya - Dataset Balancer")
    print("===================================")
    
    # Paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    orig_path = os.path.join(base_dir, 'datasets', 'career_dataset.csv')
    new_path = os.path.join(base_dir, 'expanded_career_data.csv')
    output_path = os.path.join(base_dir, 'datasets', 'career_dataset_balanced.csv')

    # 1. Load Original Data
    try:
        print(f"Loading original data from: {orig_path}")
        df_orig = pd.read_csv(orig_path, on_bad_lines='skip')
        print(f"Original Size: {len(df_orig)} rows")
    except Exception as e:
        print(f"Error loading original data: {e}")
        return

    # 2. Load New Data
    try:
        print(f"Loading new data from: {new_path}")
        df_new = pd.read_csv(new_path)
        print(f"New Data Size: {len(df_new)} rows")
    except Exception as e:
        print(f"Error loading new data: {e}")
        return

    # 3. Analyze Domains in Original
    if 'domain' in df_orig.columns:
        counts = df_orig['domain'].value_counts()
        print("\nOriginal Domain Distribution:")
        print(counts)
    else:
        print("Warning: 'domain' column missing in original data. treating as one large block.")
        df_orig['domain'] = 'Unclassified'

    # 4. Stratified Downsampling Strategy
    # We want to cap existing large domains to avoid drowning out the new ones.
    # Let's say we cap at 500 per domain.
    TARGET_CAP = 500
    
    print(f"\nDownsampling large domains to max {TARGET_CAP} entries...")
    
    balanced_frames = []
    
    # Process original data by domain
    for domain in df_orig['domain'].unique():
        domain_data = df_orig[df_orig['domain'] == domain]
        count = len(domain_data)
        
        if count > TARGET_CAP:
            # Sample it
            sampled_data = domain_data.sample(n=TARGET_CAP, random_state=42)
            balanced_frames.append(sampled_data)
            print(f"  - {domain}: Reduced {count} -> {TARGET_CAP}")
        else:
            # Keep all
            balanced_frames.append(domain_data)
            print(f"  - {domain}: Kept all {count}")

    # 5. Add 100% of New Data
    # Ensure columns match or are compatible.
    # If df_new has columns not in df_orig, they will be added (with NaNs for orig data).
    # If df_orig has columns not in df_new, they will be added (with NaNs for new data).
    
    balanced_frames.append(df_new)
    print(f"  - [NEW DATA]: Added all {len(df_new)} rows")

    # 6. Merge
    df_final = pd.concat(balanced_frames, ignore_index=True)
    
    # Final cleanup
    # Ensure critical columns exist
    critical_cols = ['career_name', 'description', 'required_skills', 'domain']
    for col in critical_cols:
        if col not in df_final.columns:
            df_final[col] = ''
    
    # Fill NaNs with empty strings for text columns
    df_final = df_final.fillna('')
    
    print(f"\nFinal Balanced Dataset Size: {len(df_final)} rows")
    print("New Domain Distribution:")
    print(df_final['domain'].value_counts())

    # 7. Save
    df_final.to_csv(output_path, index=False)
    print(f"\nSuccess! Saved balanced dataset to: {output_path}")
    print("You can now run 'python train_models.py' to train on this balanced data.")

if __name__ == "__main__":
    balance_datasets()
