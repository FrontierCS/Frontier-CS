import pandas as pd
import os

# --- Setup Paths ---
# Get the directory where this script is located (resources/)
script_dir = os.path.dirname(os.path.abspath(__file__))

# Define the datasets directory (resources/datasets/)
datasets_dir = os.path.join(script_dir, "datasets")

# [NEW] Create the directory if it doesn't exist (Safety check)
os.makedirs(datasets_dir, exist_ok=True)

input_file = os.path.join(datasets_dir, "routerbench_0shot.pkl")
full_csv_output = os.path.join(datasets_dir, "routerbench_0shot.csv")
train_output = os.path.join(datasets_dir, "routerbench_0shot_train.csv")
test_output = os.path.join(datasets_dir, "routerbench_0shot_test.csv")
test_sample_output = os.path.join(datasets_dir, "routerbench_0shot_test_500.csv")

try:
    print(f"Loading dataset from: {input_file}")
    # Load the pickle dataset
    df = pd.read_pickle(input_file)
    
    # --- 0. Convert Original to CSV ---
    df.to_csv(full_csv_output, index=False)
    print(f"Converted pickle to CSV: {full_csv_output}")

    # --- 1. Randomly sample 5% for Train (No Replacement) ---
    train_df = df.sample(frac=0.05, random_state=42)
    train_df.to_csv(train_output, index=False)
    print(f"Created 'train' split with {len(train_df)} rows.")

    # --- 2. Remaining 95% for Test (Keep Original Ordering) ---
    test_df = df.drop(train_df.index)
    test_df.to_csv(test_output, index=False)
    print(f"Created 'test' split with {len(test_df)} rows.")

    # --- 3. Randomly sample 500 rows from the Test set ---
    sample_size = 500
    if len(test_df) < sample_size:
        print(f"Warning: Test data only has {len(test_df)} rows. Sampling all of them.")
        sample_size = len(test_df)
        
    test_sample_df = test_df.sample(n=sample_size, random_state=42)
    test_sample_df.to_csv(test_sample_output, index=False)
    print(f"Created 'test_500' split with {len(test_sample_df)} rows.")

except FileNotFoundError:
    print(f"Error: The file '{input_file}' was not found. Please run the download script first.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")