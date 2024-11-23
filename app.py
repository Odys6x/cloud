import streamlit as st
import torch
import joblib
from model import ComplexTabularModel
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import json

# Shared state to hold received data
received_data = {"player_data": [], "game_stats": {}, "event_data": {}}

# Model and Scaler Setup
model = ComplexTabularModel(input_dim=12)
model.load_state_dict(torch.load("model/model.pth"))
model.eval()
scaler = joblib.load("model/scaler.pkl")

# Define HTTP server to handle POST requests
class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        global received_data
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        try:
            received_data = json.loads(post_data)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Data received")
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Invalid JSON format")

# Start HTTP server in a background thread
def start_http_server():
    server = HTTPServer(("0.0.0.0", 8501), RequestHandler)
    server.serve_forever()

threading.Thread(target=start_http_server, daemon=True).start()

# Streamlit App
st.title("League of Legends Win Prediction")
st.sidebar.header("Team Stats")
st.header("Win Probability")

# Placeholders for dynamic updates
team_order_stats_placeholder = st.sidebar.empty()
team_chaos_stats_placeholder = st.sidebar.empty()
player_stats_placeholder = st.empty()
win_prob_placeholder = st.empty()

# Gold calculation functions
def calculate_gold(player_name, minions_killed, wards_killed, game_time, event_data):
    passive_gold_per_10_seconds = 20.4
    starting_gold = 500
    passive_gold = max((game_time - 110) // 10 * passive_gold_per_10_seconds, 0) if game_time >= 110 else 0
    gold_from_minions = minions_killed * 14
    gold_from_wards = wards_killed * 30
    gold_from_events = calculate_event_gold(player_name, event_data)
    return starting_gold + passive_gold + gold_from_minions + gold_from_wards + gold_from_events

def calculate_event_gold(player_name, event_data):
    base_name = player_name.split("#")[0]
    event_gold = 0
    for event in event_data:
        if event.get("KillerName") == base_name:
            event_gold += {
                "DragonKill": 300,
                "BaronKill": 500,
                "TurretKilled": 250,
                "ChampionKill": 300,
            }.get(event.get("EventName"), 0)
        elif base_name in event.get("Assisters", []):
            event_gold += {"DragonKill": 100, "BaronKill": 200}.get(event.get("EventName"), 0)
    return event_gold

def prepare_model_input(player_data, team_order_gold, team_chaos_gold):
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
        team_order_kills, team_order_deaths, team_order_assists,
        team_order_gold, team_order_cs, team_order_kda,
        team_chaos_kills, team_chaos_deaths, team_chaos_assists,
        team_chaos_gold, team_chaos_cs, team_chaos_kda,
    ]

def predict_win_probability(model_input):
    scaled_input = scaler.transform([model_input])
    input_tensor = torch.tensor(scaled_input, dtype=torch.float32)
    with torch.no_grad():
        prediction = model(input_tensor)
        probs = torch.softmax(prediction, dim=1)
    return {
        "team_order_win": float(probs[0][1].item() * 100),
        "team_chaos_win": float(probs[0][0].item() * 100),
    }

# Auto-refresh the Streamlit UI
while True:
    if received_data.get("player_data"):
        player_data = received_data.get("player_data", [])
        game_stats = received_data.get("game_stats", {})
        event_data = received_data.get("event_data", {})
        game_time = game_stats.get("gameTime", 0)

        team_order_gold = sum(
            calculate_gold(p["summonerName"], p["scores"]["creepScore"], p["scores"]["wardScore"], game_time, event_data)
            for p in player_data if p["team"] == "ORDER"
        )
        team_chaos_gold = sum(
            calculate_gold(p["summonerName"], p["scores"]["creepScore"], p["scores"]["wardScore"], game_time, event_data)
            for p in player_data if p["team"] == "CHAOS"
        )
        model_input = prepare_model_input(player_data, team_order_gold, team_chaos_gold)
        predictions = predict_win_probability(model_input)

        team_order_stats = {
            "kills": sum(p["scores"].get("kills", 0) for p in player_data if p["team"] == "ORDER"),
            "deaths": sum(p["scores"].get("deaths", 0) for p in player_data if p["team"] == "ORDER"),
            "assists": sum(p["scores"].get("assists", 0) for p in player_data if p["team"] == "ORDER"),
            "gold": team_order_gold,
        }
        team_chaos_stats = {
            "kills": sum(p["scores"].get("kills", 0) for p in player_data if p["team"] == "CHAOS"),
            "deaths": sum(p["scores"].get("deaths", 0) for p in player_data if p["team"] == "CHAOS"),
            "assists": sum(p["scores"].get("assists", 0) for p in player_data if p["team"] == "CHAOS"),
            "gold": team_chaos_gold,
        }

        team_order_stats_placeholder.write(f"**Team Order Stats**: {team_order_stats}")
        team_chaos_stats_placeholder.write(f"**Team Chaos Stats**: {team_chaos_stats}")
        player_stats_placeholder.table(player_data)
        win_prob_placeholder.json(predictions)

    time.sleep(5)  # Update every 5 seconds
