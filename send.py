from flask import Flask, jsonify, request
import requests
from openai import OpenAI

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

        # Limit data size
        limited_data = {
            "game_stats": game_stats,
            "key_stats": {
                "total_kills": sum(p.get("scores", {}).get("kills", 0) for p in player_data),
                "game_time": game_stats.get("gameTime", 0)
            },
            "recent_events": event_data[-5:] if event_data else []
        }

        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Provide a brief game summary focusing on key events and overall game state."},
                {"role": "user", "content": str(limited_data)}
            ]
        )
        return jsonify({"summary": completion.choices[0].message.content})
    except Exception as e:
        print(f"Error details: {str(e)}")
        return jsonify({"error": "Failed to summarize data"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
