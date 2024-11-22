import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler


class Preprocessor:
    def __init__(self, scaling=True):
        """
        Initialize the preprocessor with optional scaling.
        Args:
            scaling (bool): Whether to scale numerical features.
        """
        self.scaling = scaling
        self.scaler = StandardScaler() if scaling else None

    def load_data(self, file_path):
        """
        Load the data from a CSV file.
        Args:
            file_path (str): Path to the CSV file.
        Returns:
            pd.DataFrame: Loaded data.
        """
        self.data = pd.read_csv(file_path)
        return self.data

    def combine_team_stats(self):
        """
        Combine stats of both teams into one row per match.
        Returns:
            pd.DataFrame: Data with combined team stats.
        """
        combined_rows = []
        grouped = self.data.groupby("match_id")

        for match_id, group in grouped:
            # Check if both teams are present
            if not ((group['team_id'] == 100).any() and (group['team_id'] == 200).any()):
                print(f"Skipping match {match_id} due to missing teams")
                continue

            # Get aggregated stats for Team 100 and Team 200
            team_100 = group[group['team_id'] == 100].agg({
                'kills': 'sum',
                'deaths': 'sum',
                'assists': 'sum',
                'gold_earned': 'sum',
                'cs': 'sum',
                'KDA': 'mean',
                'Kill Participation': 'mean'
            })
            team_200 = group[group['team_id'] == 200].agg({
                'kills': 'sum',
                'deaths': 'sum',
                'assists': 'sum',
                'gold_earned': 'sum',
                'cs': 'sum',
                'KDA': 'mean',
                'Kill Participation': 'mean'
            })

            # Apply gold scaling by 0.6297
            team_100_gold_scaled = team_100["gold_earned"] * 0.6297
            team_200_gold_scaled = team_200["gold_earned"] * 0.6297

            # Determine outcome (1 if Team 100 wins, else 0)
            outcome = 1 if group[group['team_id'] == 100]['outcome'].iloc[0] == "win" else 0
            duration = group["game_duration"].iloc[0]

            # Combine into one row
            combined_row = {
                "match_id": match_id,
                # Team 100 stats
                "team_100_kills": team_100["kills"],
                "team_100_deaths": team_100["deaths"],
                "team_100_assists": team_100["assists"],
                "team_100_gold": team_100_gold_scaled,  # Scaled gold for Team 100
                "team_100_cs": team_100["cs"],
                "team_100_kda": team_100["KDA"],
                # Team 200 stats
                "team_200_kills": team_200["kills"],
                "team_200_deaths": team_200["deaths"],
                "team_200_assists": team_200["assists"],
                "team_200_gold": team_200_gold_scaled,  # Scaled gold for Team 200
                "team_200_cs": team_200["cs"],
                "team_200_kda": team_200["KDA"],
                # Outcome (1 if Team 100 wins, else 0)
                "outcome": outcome
            }
            combined_rows.append(combined_row)

        self.combined_data = pd.DataFrame(combined_rows)
        return self.combined_data

    def plot_feature_importance(self):
        """
        Plot a heatmap to show feature importance by correlating with the outcome.
        """
        # Combine the features and outcome into one DataFrame
        feature_data = self.combined_data.drop(columns=["match_id"])
        feature_data["outcome"] = self.combined_data["outcome"]

        # Compute the correlation matrix
        correlation_matrix = feature_data.corr()

        # Plot the heatmap
        plt.figure(figsize=(12, 8))
        sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', fmt='.2f', linewidths=0.5)
        plt.title("Correlation Heatmap of Features with Outcome")
        plt.show()

    def add_features(self):
        """
        Add custom features such as differences in stats between teams.
        Returns:
            pd.DataFrame: Data with added features.
        """
        # Calculate Gold Per Minute for each team
        self.combined_data["team_100_gpm"] = self.combined_data["team_100_gold"] / (self.combined_data["game_duration"] / 60)
        self.combined_data["team_200_gpm"] = self.combined_data["team_200_gold"] / (self.combined_data["game_duration"] / 60)
        return self.combined_data

    def split_data(self, test_size=0.15, val_size=0.15, random_state=42):
        """
        Split the data into train, validation, and test sets.
        Args:
            test_size (float): Proportion of data for testing.
            val_size (float): Proportion of training data for validation.
            random_state (int): Seed for reproducibility.
        Returns:
            Tuple: Train, validation, and test sets (X_train, X_val, X_test, y_train, y_val, y_test).
        """
        X = self.combined_data.drop(columns=["match_id", "outcome"])
        y = self.combined_data["outcome"]

        # Split into train/test
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)

        # Further split train into train/validation
        X_train, X_val, y_train, y_val = train_test_split(X_train, y_train, test_size=val_size,
                                                          random_state=random_state)

        # Scale features if enabled
        if self.scaling:
            X_train = self.scaler.fit_transform(X_train)
            X_val = self.scaler.transform(X_val)
            X_test = self.scaler.transform(X_test)

        return X_train, X_val, X_test, y_train, y_val, y_test

# Usage Example
# preprocessor = Preprocessor(scaling=True)
# raw_data = preprocessor.load_data("data.csv")
# combined_data = preprocessor.combine_team_stats()
# combined_data = preprocessor.add_features()
# X_train, X_val, X_test, y_train, y_val, y_test = preprocessor.split_data()
