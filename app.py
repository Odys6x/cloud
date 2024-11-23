import time

import streamlit as st
import requests
import torch
import joblib
from model import ComplexTabularModel

# Public Flask API URL
flask_url = "https://69f8-202-166-153-36.ngrok-free.app/data"

# Load the trained model and scaler
model = ComplexTabularModel(input_dim=12)  # Adjust input_dim as needed
model.load_state_dict(torch.load("model/model.pth"))
model.eval()
scaler = joblib.load("model/scaler.pkl")

st.title("League of Legends Win Prediction")
st.sidebar.header("Team Stats")
st.header("Win Probability")

# Placeholders for dynamic updates
team_order_stats_placeholder = st.sidebar.empty()
team_chaos_stats_placeholder = st.sidebar.empty()
player_stats_placeholder = st.empty()
win_prob_placeholder = st.empty()

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

    # Passive gold calculation
    if game_time >= 110:  # Assume passive gold starts at 110 seconds
        elapsed_passive_time = game_time - 110
        passive_gold = (elapsed_passive_time // 10) * passive_gold_per_10_seconds
    else:
        passive_gold = 0

    # Gold from other sources
    gold_from_minions = minions_killed * 14
    gold_from_wards = wards_killed * 30
    gold_from_events = calculate_event_gold(player_name, event_data)

    return starting_gold + passive_gold + gold_from_minions + gold_from_wards + gold_from_events

def calculate_event_gold(player_name, event_data):
    """Calculate gold from events."""
    base_name = player_name.split("#")[0]  # Remove trailing identifier if present
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
        team_order_kills,
        team_order_deaths,
        team_order_assists,
        team_order_gold,
        team_order_cs,
        team_order_kda,
        team_chaos_kills,
        team_chaos_deaths,
        team_chaos_assists,
        team_chaos_gold,
        team_chaos_cs,
        team_chaos_kda,
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

# Main loop
while True:
    data = fetch_data()
    if data:
        player_data = data.get("player_data", [])
        game_stats = data.get("game_stats", {})
        event_data = data.get("event_data", {})
        game_time = game_stats.get("gameTime", 0)

        team_order_gold = sum(
            calculate_gold(p["summonerName"], p["scores"]["creepScore"], p["scores"]["wardScore"], game_time, event_data)
            for p in player_data if p["team"] == "ORDER"
        )
        team_chaos_gold = sum(
            calculate_gold(p["summonerName"], p["scores"]["creepScore"], p["scores"]["wardScore"], game_time, event_data)
            for p in player_data if p["team"] == "CHAOS"
        )
        team_order_kills = sum(p["scores"].get("kills", 0) for p in player_data if p["team"] == "ORDER")
        team_order_deaths = sum(p["scores"].get("deaths", 0) for p in player_data if p["team"] == "ORDER")
        team_order_assists = sum(p["scores"].get("assists", 0) for p in player_data if p["team"] == "ORDER")
        team_order_kda = round(
            (team_order_kills + team_order_assists) / (team_order_deaths if team_order_deaths > 0 else 1), 2)

        team_chaos_kills = sum(p["scores"].get("kills", 0) for p in player_data if p["team"] == "CHAOS")
        team_chaos_deaths = sum(p["scores"].get("deaths", 0) for p in player_data if p["team"] == "CHAOS")
        team_chaos_assists = sum(p["scores"].get("assists", 0) for p in player_data if p["team"] == "CHAOS")
        team_chaos_kda = round(
            (team_chaos_kills + team_chaos_assists) / (team_chaos_deaths if team_chaos_deaths > 0 else 1), 2)

        model_input = prepare_model_input(player_data, team_order_gold, team_chaos_gold)
        predictions = predict_win_probability(model_input)

        team_order_stats_placeholder.write("### Team Order Stats")
        team_order_stats_placeholder.json({
            "Kills": team_order_kills,
            "Deaths": team_order_deaths,
            "Assists": team_order_assists,
            "Gold": team_order_gold,
            "KDA": team_order_kda
        })

        team_chaos_stats_placeholder.write("### Team Chaos Stats")
        team_chaos_stats_placeholder.json({
            "Kills": team_chaos_kills,
            "Deaths": team_chaos_deaths,
            "Assists": team_chaos_assists,
            "Gold": team_chaos_gold,
            "KDA": team_chaos_kda
        })
        player_stats_placeholder.table(player_data)
        win_prob_placeholder.json(predictions)
    else:
        st.write("Waiting for data...")
    time.sleep(5)  # Refresh every 5 seconds
