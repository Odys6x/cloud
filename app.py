import time
import streamlit as st
import requests
import torch
import joblib
import plotly.graph_objects as go
import plotly.express as px
from model import ComplexTabularModel

# Public Flask API URL
flask_url = "https://fafd-151-192-226-94.ngrok-free.app"

# Load the trained model and scaler
model = ComplexTabularModel(input_dim=12)  # Adjust input_dim as needed
model.load_state_dict(torch.load("model/model.pth"))
model.eval()
scaler = joblib.load("model/scaler.pkl")

st.set_page_config(layout="wide")
st.title("League of Legends Win Prediction")

# Initialize session state for storing historical data
if 'historical_predictions' not in st.session_state:
    st.session_state.historical_predictions = []

# Create tabs for different visualizations
tab1, tab2 = st.tabs(["Current State", "Timeline"])


def fetch_data():
    """Fetch data from the Flask app."""
    try:
        response = requests.get(flask_url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return {}


def calculate_gold(player_name, minions_killed, wards_killed, game_time, event_data):
    """Estimate gold for a player."""
    passive_gold_per_10_seconds = 20.4
    starting_gold = 500

    if game_time >= 110:
        elapsed_passive_time = game_time - 110
        passive_gold = (elapsed_passive_time // 10) * passive_gold_per_10_seconds
    else:
        passive_gold = 0

    gold_from_minions = minions_killed * 14
    gold_from_wards = wards_killed * 30
    gold_from_events = calculate_event_gold(player_name, event_data)

    return starting_gold + passive_gold + gold_from_minions + gold_from_wards + gold_from_events


def calculate_event_gold(player_name, event_data):
    """Calculate gold from events."""
    base_name = player_name.split("#")[0]
    event_gold = 0

    for event in event_data:
        if not isinstance(event, dict):
            continue
        if event.get("KillerName") == base_name:
            if event.get("EventName") == "DragonKill":
                event_gold += 300
            elif event.get("EventName") == "BaronKill":
                event_gold += 500
            elif event.get("EventName") == "TurretKilled":
                event_gold += 250
            elif event.get("EventName") == "ChampionKill":
                event_gold += 300
        elif base_name in event.get("Assisters", []):
            if event.get("EventName") == "DragonKill":
                event_gold += 100
            elif event.get("EventName") == "BaronKill":
                event_gold += 200

    return event_gold


def prepare_model_input(player_data, team_order_gold, team_chaos_gold):
    """Prepare input features for the model."""
    team_order_kills = sum(p["scores"].get("kills", 0) for p in player_data if p["team"] == "ORDER")
    team_order_deaths = sum(p["scores"].get("deaths", 0) for p in player_data if p["team"] == "ORDER")
    team_order_assists = sum(p["scores"].get("assists", 0) for p in player_data if p["team"] == "ORDER")
    team_order_cs = sum(p["scores"].get("creepScore", 0) for p in player_data if p["team"] == "ORDER")
    team_order_kda = team_order_kills / (team_order_deaths if team_order_deaths > 0 else 1)

    team_chaos_kills = sum(p["scores"].get("kills", 0) for p in player_data if p["team"] == "CHAOS")
    team_chaos_deaths = sum(p["scores"].get("deaths", 0) for p in player_data if p["team"] == "CHAOS")
    team_chaos_assists = sum(p["scores"].get("assists", 0) for p in player_data if p["team"] == "CHAOS")
    team_chaos_cs = sum(p["scores"].get("creepScore", 0) for p in player_data if p["team"] == "CHAOS")
    team_chaos_kda = team_chaos_kills / (team_chaos_deaths if team_chaos_deaths > 0 else 1)

    return [
        team_order_kills, team_order_deaths, team_order_assists, team_order_gold,
        team_order_cs, team_order_kda, team_chaos_kills, team_chaos_deaths,
        team_chaos_assists, team_chaos_gold, team_chaos_cs, team_chaos_kda,
    ]


def predict_win_probability(model_input):
    """Use the model to predict win probabilities."""
    scaled_input = scaler.transform([model_input])
    input_tensor = torch.tensor(scaled_input, dtype=torch.float32)
    with torch.no_grad():
        prediction = model(input_tensor)
        temperature = 3.0
        probs = torch.softmax(prediction / temperature, dim=1)
    return {
        "team_order_win": float(probs[0][1].item() * 100),
        "team_chaos_win": float(probs[0][0].item() * 100),
    }


def display_team_players(players, team_name):
    """Display player statistics in a formatted way."""
    st.subheader(f"Team {team_name}")

    for player in players:
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])

        kda = f"{player['scores'].get('kills', 0)}/{player['scores'].get('deaths', 0)}/{player['scores'].get('assists', 0)}"
        kda_ratio = (player['scores'].get('kills', 0) + player['scores'].get('assists', 0)) / (
            player['scores'].get('deaths', 0) if player['scores'].get('deaths', 0) > 0 else 1)

        with col1:
            st.write(player['summonerName'])
        with col2:
            st.write(f"KDA: {kda}")
        with col3:
            st.write(f"Ratio: {kda_ratio:.2f}")
        with col4:
            st.write(f"Gold: {player.get('calculated_gold', 0):,.0f}")


# Main loop
while True:
    data = fetch_data()
    if data:
        player_data = data.get("player_data", [])
        game_stats = data.get("game_stats", {})
        event_data = data.get("event_data", {})
        game_time = game_stats.get("gameTime", 0)

        # Calculate team stats
        team_order_players = [p for p in player_data if p["team"] == "ORDER"]
        team_chaos_players = [p for p in player_data if p["team"] == "CHAOS"]

        # Calculate gold for each player
        for player in player_data:
            player['calculated_gold'] = calculate_gold(
                player["summonerName"],
                player["scores"]["creepScore"],
                player["scores"]["wardScore"],
                game_time,
                event_data
            )

        team_order_gold = sum(p['calculated_gold'] for p in team_order_players)
        team_chaos_gold = sum(p['calculated_gold'] for p in team_chaos_players)

        # Get predictions
        model_input = prepare_model_input(player_data, team_order_gold, team_chaos_gold)
        predictions = predict_win_probability(model_input)

        # Store historical data
        st.session_state.historical_predictions.append({
            'time': game_time,
            'order_win': predictions['team_order_win'],
            'chaos_win': predictions['team_chaos_win']
        })

        # Display current state tab
        with tab1:
            # Create two columns for the win prediction pie chart and team stats
            col1, col2 = st.columns([1, 2])

            with col1:
                # Create pie chart using plotly
                fig = go.Figure(data=[go.Pie(
                    labels=['Team Order', 'Team Chaos'],
                    values=[predictions['team_order_win'], predictions['team_chaos_win']],
                    hole=.3
                )])
                fig.update_layout(title='Win Probability')
                st.plotly_chart(fig)

            with col2:
                # Display team stats
                col_order, col_chaos = st.columns(2)

                with col_order:
                    display_team_players(team_order_players, "ORDER")

                with col_chaos:
                    display_team_players(team_chaos_players, "CHAOS")

        # Display timeline tab
        with tab2:
            if len(st.session_state.historical_predictions) > 1:
                # Create line chart using plotly
                df_timeline = pd.DataFrame(st.session_state.historical_predictions)
                fig = px.line(df_timeline,
                              x='time',
                              y=['order_win', 'chaos_win'],
                              labels={'value': 'Win Probability (%)', 'time': 'Game Time (s)'},
                              title='Win Probability Over Time')
                st.plotly_chart(fig)

    else:
        st.write("Waiting for data...")

    time.sleep(5)  # Refresh every 5 seconds