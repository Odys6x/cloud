from flask import Flask, render_template, jsonify, request
import torch
import joblib
from model import ComplexTabularModel

app = Flask(__name__)

model = ComplexTabularModel(input_dim=12)
model.load_state_dict(torch.load("model/model.pth"))
model.eval()
scaler = joblib.load("model/scaler.pkl")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/live-data", methods=["POST"])
def live_data():
    # Get data from the incoming request
    data = request.json
    if not data:
        return jsonify({"error": "No data received"}), 400

    player_data = data.get("player_data", [])
    game_stats = data.get("game_stats", {})
    event_data = data.get("event_data", [])
    game_time = game_stats.get("gameTime", 0)

    # Estimate gold and calculate stats
    team_order_gold, team_chaos_gold, player_stats = calculate_gold_and_stats(player_data, event_data, game_time)

    # Prepare the input for the model
    model_input = prepare_model_input(player_data, team_order_gold, team_chaos_gold)

    # Predict win probabilities
    predictions = predict_win_probability(model_input)

    # Prepare team stats
    team_order_stats = {
        "kills": sum(p.get("scores", {}).get("kills", 0) for p in player_data if p["team"] == "ORDER"),
        "deaths": sum(p.get("scores", {}).get("deaths", 0) for p in player_data if p["team"] == "ORDER"),
        "assists": sum(p.get("scores", {}).get("assists", 0) for p in player_data if p["team"] == "ORDER"),
        "gold": team_order_gold,
    }
    team_chaos_stats = {
        "kills": sum(p.get("scores", {}).get("kills", 0) for p in player_data if p["team"] == "CHAOS"),
        "deaths": sum(p.get("scores", {}).get("deaths", 0) for p in player_data if p["team"] == "CHAOS"),
        "assists": sum(p.get("scores", {}).get("assists", 0) for p in player_data if p["team"] == "CHAOS"),
        "gold": team_chaos_gold,
    }

    return jsonify({
        "predictions": predictions,
        "team_order_stats": team_order_stats,
        "team_chaos_stats": team_chaos_stats,
        "player_stats": player_stats,
    })

def calculate_gold_and_stats(player_data, event_data, game_time):
    team_order_gold = 0
    team_chaos_gold = 0
    player_stats = []

    for player in player_data:
        team = player["team"]
        summoner_name = player["summonerName"]
        creep_score = player["scores"].get("creepScore", 0)
        ward_score = player["scores"].get("wardScore", 0)

        # Estimate gold for each player
        estimated_gold = estimate_gold(summoner_name, creep_score, ward_score, game_time, event_data)

        if team == "ORDER":
            team_order_gold += estimated_gold
        else:
            team_chaos_gold += estimated_gold

        # Format player stats
        kills = player["scores"].get("kills", 0)
        deaths = player["scores"].get("deaths", 0)
        assists = player["scores"].get("assists", 0)
        kda_score = f"{kills}/{deaths}/{assists}"
        player_stats.append({
            "champion": player["championName"],
            "summoner": summoner_name,
            "team": team,
            "kda": kda_score,
            "gold": estimated_gold,
        })

    return team_order_gold, team_chaos_gold, player_stats

def estimate_gold(player_name, minions_killed, wards_killed, game_time, event_data):
    passive_gold_per_10_seconds = 20.4
    starting_gold = 500

    # Calculate passive gold
    if game_time >= 110:
        elapsed_passive_time = game_time - 110
        passive_gold = (elapsed_passive_time // 10) * passive_gold_per_10_seconds
    else:
        passive_gold = 0

    # Calculate gold from other sources
    gold_from_minions = minions_killed * 14
    gold_from_ward_kills = wards_killed * 30
    gold_from_events = calculate_event_gold(player_name, event_data)

    total_gold = starting_gold + passive_gold + gold_from_minions + gold_from_ward_kills + gold_from_events
    return total_gold

def calculate_event_gold(player_name, event_data):
    base_player_name = player_name.split("#")[0]
    event_gold = 0

    for event in event_data:
        if event.get("Acer") == base_player_name and event["EventName"] == "Ace":
            event_gold += 150
        if event.get("KillerName") == base_player_name:
            if event["EventName"] == "DragonKill":
                event_gold += 300
            elif event["EventName"] == "BaronKill":
                event_gold += 500
            elif event["EventName"] == "TurretKilled":
                event_gold += 250
            elif event["EventName"] == "InhibKilled":
                event_gold += 400
            elif event["EventName"] == "ChampionKill":
                event_gold += 300
            elif event["EventName"] == "FirstBlood":
                event_gold += 400
        elif base_player_name in event.get("Assisters", []):
            if event["EventName"] == "DragonKill":
                event_gold += 100
            elif event["EventName"] == "BaronKill":
                event_gold += 200

    return event_gold

def prepare_model_input(player_data, team_order_gold, team_chaos_gold):
    # Prepare model input features
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

if __name__ == "__main__":
    app.run(debug=True)
