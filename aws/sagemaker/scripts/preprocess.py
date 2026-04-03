"""SageMaker Processing Job — Data Preprocessing."""
import argparse
import os
import pandas as pd
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=str, default="/opt/ml/processing/input")
    parser.add_argument("--output-dir", type=str, default="/opt/ml/processing/output")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load all CSVs from input directory
    csv_files = sorted(input_dir.glob("*.csv"))
    dfs = [pd.read_csv(f) for f in csv_files]
    df = pd.concat(dfs, ignore_index=True)

    # 2. Clean invalid GPS coordinates (latitude=99, longitude=999)
    df = df[(df["latitude"] != 99) & (df["longitude"] != 999)]

    # 3. Clean timeout values (svr1-svr4 = 1000)
    for col in ["svr1", "svr2", "svr3", "svr4"]:
        if col in df.columns:
            df = df[df[col] != 1000]

    # 4. Drop rows with NaN in critical columns
    df = df.dropna(subset=["latitude", "longitude"])

    # 5. Save cleaned output
    df.to_csv(output_dir / "cleaned_data.csv", index=False)
    print(f"Preprocessing complete. Output rows: {len(df)}")

if __name__ == "__main__":
    main()

