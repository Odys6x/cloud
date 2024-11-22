import pandas as pd

# Load data
df = pd.read_csv("match_results_with_objectives.csv")

# Print original count
print(f"Original number of rows: {len(df)}")

# Remove games under 5 minutes (300 seconds)
df_cleaned = df[df['game_duration'] >= 300]

# Reset index after filtering
df_cleaned = df_cleaned.reset_index(drop=True)

# Print results
print(f"Number of rows after removing short games: {len(df_cleaned)}")
print(f"Number of rows removed: {len(df) - len(df_cleaned)}")

# Save cleaned data
df_cleaned.to_csv("cleaned_match_results.csv", index=False)
print("\nCleaned data saved to 'cleaned_match_results.csv'")