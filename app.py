import time
import streamlit as st
import requests
import torch
import joblib
import plotly.graph_objects as go
import plotly.express as px
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
        fig = go.Figure(data=[
            go.Bar(name='Team Order',
                   x=['Win Probability'],
                   y=[predictions['team_order_win']],
                   marker_color='blue'),
            go.Bar(name='Team Chaos',
                   x=['Win Probability'],
                   y=[predictions['team_chaos_win']],
                   marker_color='red')
        ])
        fig.update_layout(
            barmode='group',
            title='Win Probability by Team',
            yaxis_title='Probability (%)',
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

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=st.session_state.game_times,
            y=[pred[0] for pred in st.session_state.historical_predictions],
            name='Team Order',
            line=dict(color='blue')
        ))
        fig.add_trace(go.Scatter(
            x=st.session_state.game_times,
            y=[pred[1] for pred in st.session_state.historical_predictions],
            name='Team Chaos',
            line=dict(color='red')
        ))
        fig.update_layout(
            title='Win Probability Over Time',
            xaxis_title='Game Time (seconds)',
            yaxis_title='Probability (%)',
            height=400
        )

    return fig


def display_player_card(player, team_color):
    """Create a styled card for player information."""
    with st.container():
        cols = st.columns([2, 1, 1, 1])
        with cols[0]:
            st.markdown(f"**{player['summonerName']}**")
        with cols[1]:
            st.metric("KDA",
                      f"{player['scores'].get('kills', 0)}/{player['scores'].get('deaths', 0)}/{player['scores'].get('assists', 0)}")
        with cols[2]:
            st.metric("Gold", f"{player.get('calculated_gold', 0):,.0f}")
        with cols[3]:
            st.metric("CS", player['scores'].get('creepScore', 0))

        # Add items if available
        if 'items' in player:
            st.write("Items:", ", ".join(player['items']))
        st.markdown("---")


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

        team_order_gold = sum(p['calculated_gold'] for p in player_data if p["team"] == "ORDER")
        team_chaos_gold = sum(p['calculated_gold'] for p in player_data if p["team"] == "CHAOS")

        model_input = prepare_model_input(player_data, team_order_gold, team_chaos_gold)
        predictions = predict_win_probability(model_input)

        # Display win probability chart
        with win_prob_tab:
            fig = create_win_probability_chart(predictions, chart_type)
            st.plotly_chart(fig, use_container_width=True)

            # Display overall team stats
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### Team Order Overall")
                st.json({
                    "Total Gold": f"{team_order_gold:,.0f}",
                    "Total Kills": sum(p["scores"].get("kills", 0) for p in player_data if p["team"] == "ORDER"),
                    "Total Deaths": sum(p["scores"].get("deaths", 0) for p in player_data if p["team"] == "ORDER"),
                    "Total Assists": sum(p["scores"].get("assists", 0) for p in player_data if p["team"] == "ORDER")
                })
            with col2:
                st.markdown("### Team Chaos Overall")
                st.json({
                    "Total Gold": f"{team_chaos_gold:,.0f}",
                    "Total Kills": sum(p["scores"].get("kills", 0) for p in player_data if p["team"] == "CHAOS"),
                    "Total Deaths": sum(p["scores"].get("deaths", 0) for p in player_data if p["team"] == "CHAOS"),
                    "Total Assists": sum(p["scores"].get("assists", 0) for p in player_data if p["team"] == "CHAOS")
                })

        # Display team details
        with teams_tab:
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### Team Order")
                for player in player_data:
                    if player["team"] == "ORDER":
                        display_player_card(player, "blue")

            with col2:
                st.markdown("### Team Chaos")
                for player in player_data:
                    if player["team"] == "CHAOS":
                        display_player_card(player, "red")

    else:
        st.write("Waiting for data...")
    time.sleep(5)