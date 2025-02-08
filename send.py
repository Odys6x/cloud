from flask import Flask, jsonify, request
import requests
from openai import OpenAI
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# OpenAI API Key
client = OpenAI(api_key="")

# URLs for data fetching
player_url = "https://127.0.0.1:2999/liveclientdata/playerlist"
game_stats_url = "https://127.0.0.1:2999/liveclientdata/gamestats"
event_url = "https://127.0.0.1:2999/liveclientdata/eventdata"

def fetch_data(url):
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        return {}


@app.route('/data', methods=['GET'])
def get_data():
    player_data = fetch_data(player_url)
    game_stats = fetch_data(game_stats_url)
    event_data = fetch_data(event_url)

    return jsonify({
        "player_data": player_data,
        "game_stats": game_stats,
        "event_data": event_data
    })


@app.route('/summarize', methods=['GET'])
def summarize_data():
    try:
        player_data = fetch_data(player_url)
        game_stats = fetch_data(game_stats_url)
        event_data = fetch_data(event_url)

        # Simplify and reduce player data
        simplified_players = []
        for player in player_data:
            simplified_players.append({
                "name": player.get("summonerName", ""),
                "champion": player.get("championName", ""),
                "team": player.get("team", ""),
                "kda": f"{player.get('scores', {}).get('kills', 0)}/{player.get('scores', {}).get('deaths', 0)}/{player.get('scores', {}).get('assists', 0)}"
            })

        # Take only essential game stats
        simplified_game_stats = {
            "gameTime": game_stats.get("gameTime", 0),
            "gameMode": game_stats.get("gameMode", "")
        }

        # Take only significant events
        significant_events = []
        if isinstance(event_data, list):
            for event in event_data[-3:]:  # Only last 3 events
                if event.get("EventName") in ["ChampionKill", "DragonKill", "BaronKill", "TurretKilled"]:
                    significant_events.append({
                        "type": event.get("EventName"),
                        "killer": event.get("KillerName")
                    })

        limited_data = {
            "game": simplified_game_stats,
            "players": simplified_players,
            "key_events": significant_events
        }

        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Provide a 2-3 sentence game summary focusing only on the most important events and state."},
                {"role": "user", "content": str(limited_data)}
            ]
        )
        return jsonify({"summary": completion.choices[0].message.content})
    except Exception as e:
        print(f"Error details: {str(e)}")
        return jsonify({"error": "Failed to summarize data"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
