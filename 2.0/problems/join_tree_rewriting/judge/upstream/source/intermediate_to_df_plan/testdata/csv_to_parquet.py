import os
import pandas as pd
from pathlib import Path


def convert_csv_to_parquet(input_folder: str, output_folder: str):
    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Get a list of all CSV files in the input folder
    csv_files = [f for f in os.listdir(input_folder) if f.endswith(".csv")]

    # Convert each CSV file to a Parquet file
    for csv_file in csv_files:
        csv_path = os.path.join(input_folder, csv_file)
        parquet_path = os.path.join(output_folder, Path(csv_file).stem + ".parquet")

        # Read the CSV file
        df = pd.read_csv(csv_path)

        # Write the DataFrame to a Parquet file
        df.to_parquet(parquet_path, compression="gzip")
        print(f"Converted {csv_file} to {parquet_path}")

    print(
        f"All CSV files in {input_folder} have been converted to Parquet format in {output_folder}"
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert CSV files to Parquet format")
    parser.add_argument("-i", "--input_folder", type=str, help="Folder containing CSV files")
    parser.add_argument("-o", "--output_folder", type=str, help="Folder to save Parquet files")

    args = parser.parse_args()

    convert_csv_to_parquet(args.input_folder, args.output_folder)
