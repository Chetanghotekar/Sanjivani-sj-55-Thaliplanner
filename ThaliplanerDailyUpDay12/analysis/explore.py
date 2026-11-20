"""Day 4: Basic Pandas analysis of recipe records."""
import pandas as pd
from app.records import load_records

def main():
    df = pd.DataFrame(load_records())
    if df.empty:
        print("No records available. Run the Day 3 ingest pipeline first.")
        return
    print("\nFact 1 - Total recipes:", len(df))
    print("\nFact 2 - Recipes by category:")
    print(df["region_or_type"].fillna("Unknown").value_counts().to_string())
    numeric_servings = pd.to_numeric(df["servings"], errors="coerce")
    print("\nFact 3 - Average servings:", round(numeric_servings.mean(), 2) if numeric_servings.notna().any() else "Not available")

if __name__ == "__main__":
    main()
