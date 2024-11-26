import time
import streamlit as st
import requests
import torch
import joblib
import pandas as pd
from model import ComplexTabularModel

# Public Flask API URL
flask_url = "https://0dfd-151-192-226-94.ngrok-free.app/data"

# Load the trained model and scaler
model = ComplexTabularModel(input_dim=12)
model.load_state_dict(torch.load("model/model.pth"))
model.eval()
scaler = joblib.load("model/scaler.pkl")

# Page config
st.set_page_config(layout="wide")
st.title("League of Legends Win Prediction")

# Initialize session state for historical data
if 'historical_predictions' not in st.session_state:
    st.session_state.historical_predictions = []
    st.session_state.game_times = []

# Create tabs for different visualizations
win_prob_tab, teams_tab = st.tabs(["Win Probability", "Team Details"])

# Select chart type
with win_prob_tab:
    chart_type = st.radio("Select Chart Type", ["Bar Chart", "Line Chart"], horizontal=True)


def create_win_probability_chart(predictions, chart_type="Bar Chart"):
    """Create either a bar chart or line chart for win probabilities."""
    if chart_type == "Bar Chart":
        # Create DataFrame for bar chart
        df = pd.DataFrame({
            'Team': ['Team Order', 'Team Chaos'],
            'Win Probability': [
                predictions['team_order_win'],
                predictions['team_chaos_win']
            ]
        })
        return st.bar_chart(
            df.set_index('Team'),
            height=400
        )
    else:  # Line Chart
        # Add current predictions to historical data
        current_time = len(st.session_state.historical_predictions) * 5  # 5 second intervals
        st.session_state.game_times.append(current_time)
        st.session_state.historical_predictions.append([
            predictions['team_order_win'],
            predictions['team_chaos_win']
        ])

        # Create DataFrame for line chart
        df = pd.DataFrame(
            st.session_state.historical_predictions,
            columns=['Team Order', 'Team Chaos']
        )
        df.index = st.session_state.game_times
        return st.line_chart(df, height=400)


def display_player_card(player):
    """Create a styled card for player information."""
    with st.container():
        # Player name and basic stats
        st.markdown(f"""
        <div style='padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin: 5px;'>
            <h3 style='margin: 0;'>{player['summonerName']}</h3>
            <table style='width: 100%;'>
                <tr>
                    <td><b>KDA:</b> {player['scores'].get('kills', 0)}/{player['scores'].get('deaths', 0)}/{player['scores'].get('assists', 0)}</td>
                    <td><b>Gold:</b> {player.get('calculated_gold', 0):,.0f}</td>
                    <td><b>CS:</b> {player['scores'].get('creepScore', 0)}</td>
                </tr>
            </table>
        </div>
        """, unsafe_allow_html=True)


def display_team_stats(team_data, team_name, team_gold):
    """Display team statistics in a formatted way."""
    total_kills = sum(p["scores"].get("kills", 0) for p in team_data)
    total_deaths = sum(p["scores"].get("deaths", 0) for p in team_data)
    total_assists = sum(p["scores"].get("assists", 0) for p in team_data)

    st.markdown(f"### {team_name}")
    cols = st.columns(4)
    cols[0].metric("Total Gold", f"{team_gold:,.0f}")
    cols[1].metric("Kills", total_kills)
    cols[2].metric("Deaths", total_deaths)
    cols[3].metric("Assists", total_assists)

    st.markdown("---")
    return total_kills, total_deaths, total_assists


# Main loop
while True:
    data = fetch_data()
    if data:
        player_data = data.get("player_data", [])
        game_stats = data.get("game_stats", {})
        event_data = data.get("event_data", {})
        game_time = game_stats.get("gameTime", 0)

        # Calculate gold and prepare data
        for player in player_data:
            player['calculated_gold'] = calculate_gold(
                player["summonerName"],
                player["scores"]["creepScore"],
                player["scores"]["wardScore"],
                game_time,
                event_data
            )

        # Separate teams
        team_order_players = [p for p in player_data if p["team"] == "ORDER"]
        team_chaos_players = [p for p in player_data if p["team"] == "CHAOS"]

        team_order_gold = sum(p['calculated_gold'] for p in team_order_players)
        team_chaos_gold = sum(p['calculated_gold'] for p in team_chaos_players)

        model_input = prepare_model_input(player_data, team_order_gold, team_chaos_gold)
        predictions = predict_win_probability(model_input)

        # Display win probability chart
        with win_prob_tab:
            create_win_probability_chart(predictions, chart_type)

            # Display team overall stats
            st.markdown("### Team Statistics")
            col1, col2 = st.columns(2)

            with col1:
                order_k, order_d, order_a = display_team_stats(
                    team_order_players, "Team Order", team_order_gold
                )

            with col2:
                chaos_k, chaos_d, chaos_a = display_team_stats(
                    team_chaos_players, "Team Chaos", team_chaos_gold
                )

        # Display team details
        with teams_tab:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### Team Order")
                for player in team_order_players:
                    display_player_card(player)

            with col2:
                st.markdown("### Team Chaos")
                for player in team_chaos_players:
                    display_player_card(player)

    else:
        st.write("Waiting for data...")
    time.sleep(5)