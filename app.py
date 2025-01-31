import time
import streamlit as st
import requests
import torch
import joblib
import pandas as pd
from model import ComplexTabularModel
import altair as alt


flask_url = "https://94b8-42-60-47-213.ngrok-free.app/data"
summary_url = "https://94b8-42-60-47-213.ngrok-free.app/summarize"

def fetch_data():
    try:
        response = requests.get(flask_url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return {}

def fetch_summary():
    """Fetch summary data from the /summarize endpoint."""
    try:
        response = requests.get(summary_url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching summary: {e}")
        return {}


def calculate_event_gold(player_name, event_data):
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


def predict_win_probability(model_input,game_time):
    """Use the model to predict win probabilities."""
    scaled_input = scaler.transform([model_input])
    input_tensor = torch.tensor(scaled_input, dtype=torch.float32)
    with torch.no_grad():
        prediction = model(input_tensor)
        temperature = time_based_temperature(game_time)
        probs = torch.softmax(prediction / temperature, dim=1)
    return {
        "team_order_win": float(probs[0][1].item() * 100),
        "team_chaos_win": float(probs[0][0].item() * 100),
    }

def create_win_probability_chart(predictions, chart_type="Bar Chart"):
    """Create either a bar chart or line chart for win probabilities."""
    if chart_type == "Bar Chart":
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
        current_time = len(st.session_state.historical_predictions) * 5
        st.session_state.game_times.append(current_time)
        st.session_state.historical_predictions.append([
            predictions['team_order_win'],
            predictions['team_chaos_win']
        ])

        # Create DataFrame for the chart
        df = pd.DataFrame({
            'Time': st.session_state.game_times,
            'Team Order': [pred[0] for pred in st.session_state.historical_predictions],
            'Team Chaos': [pred[1] for pred in st.session_state.historical_predictions]
        })

        # Melt the DataFrame to create a format suitable for Altair
        df_melted = pd.melt(df, id_vars=['Time'], value_vars=['Team Order', 'Team Chaos'], 
                           var_name='Team', value_name='Win Probability')

        # Create Altair chart
        chart = alt.Chart(df_melted).mark_line(point=True).encode(
            x=alt.X('Time:Q', title='Game Time (seconds)'),
            y=alt.Y('Win Probability:Q', title='Win Probability (%)'),
            color=alt.Color('Team:N'),
            tooltip=['Team:N', 'Win Probability:Q', 'Time:Q']
        ).properties(
            height=400
        )

        st.altair_chart(chart, use_container_width=True)

        # Display current values
        st.markdown(f"""
        Current Probabilities:
        - Team Order: {predictions['team_order_win']:.1f}%
        - Team Chaos: {predictions['team_chaos_win']:.1f}%
        """)

def time_based_temperature(game_time, max_temp=3.0, min_temp=1.0, max_time=10):
    if game_time >= max_time:
        return min_temp
    else:
        decay_ratio = game_time / max_time
        return max_temp - decay_ratio * (max_temp - min_temp)


def get_champion_image_url(champion_name):
    """Convert champion name to proper format for image URL."""
    # Handle special cases
    name_corrections = {
        "Nunu & Willump": "Nunu",
        "Renata Glasc": "Renata",
        "Wukong": "MonkeyKing",
        # Add more special cases as needed
    }

    # Use corrected name if it exists, otherwise use original
    champion_name = name_corrections.get(champion_name, champion_name)

    # Remove spaces and special characters
    champion_name = champion_name.replace(" ", "").replace("'", "").replace(".", "")

    # Using the tile endpoint with latest patch
    return f"https://cdn.communitydragon.org/latest/champion/{champion_name}/portrait"


def display_player_card(player):
    """Create a styled card for player information."""
    with st.container():
        # Main card container
        with st.container():
            st.markdown("""
            <div style='padding: 10px; border: 1px solid #ddd; border-radius: 5px; margin: 5px;'>
            """, unsafe_allow_html=True)

            # Player info row with flex layout
            cols = st.columns([1, 5])

            # Champion portrait
            with cols[0]:
                champion_name = player.get('championName', 'Unknown')
                try:
                    champion_img_url = f"https://cdn.communitydragon.org/latest/champion/{champion_name}/portrait"
                    st.image(champion_img_url, width=60)
                except Exception as e:
                    st.write(f"Champion: {champion_name}")

            # Player details
            with cols[1]:
                st.markdown(f"""
                    <h3 style='margin: 0;'>{player['summonerName']}</h3>
                    <p style='margin: 5px 0;'><b>Champion:</b> {champion_name}</p>
                    <div style='display: flex; justify-content: space-between; margin: 10px 0;'>
                        <div><b>KDA:</b> {player['scores'].get('kills', 0)}/{player['scores'].get('deaths', 0)}/{player['scores'].get('assists', 0)}</div>
                        <div><b>Gold:</b> {player.get('calculated_gold', 0):,.0f}</div>
                        <div><b>CS:</b> {player['scores'].get('creepScore', 0)}</div>
                    </div>
                """, unsafe_allow_html=True)

            # Items section
            if 'items' in player and player['items']:
                st.markdown("""
                <div style='margin-top: 10px; padding-top: 10px; border-top: 1px solid #eee;'>
                    <h4 style='margin: 0 0 10px 0;'>Items</h4>
                </div>
                """, unsafe_allow_html=True)

                # Create columns for items
                item_cols = st.columns(7)
                for item in player['items']:
                    if isinstance(item, dict) and item.get('displayName'):
                        slot = item.get('slot', 0)
                        if 0 <= slot < 7:
                            with item_cols[slot]:
                                st.markdown(f"""
                                <div style='padding: 5px; border: 1px solid #ddd; border-radius: 3px; margin: 2px;'>
                                    <p style='font-size: 12px; margin: 0;'>{item['displayName']}</p>
                                    <p style='font-size: 10px; color: gray; margin: 0;'>Cost: {item['price']}g</p>
                                </div>
                                """, unsafe_allow_html=True)

            # Close the main container
            st.markdown("</div>", unsafe_allow_html=True)

def display_team_stats(team_data, team_name, team_gold):
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


model = ComplexTabularModel(input_dim=12)
model.load_state_dict(torch.load("model/model.pth"))
model.eval()
scaler = joblib.load("model/scaler.pkl")

st.set_page_config(layout="wide")
st.title("League of Legends Win Prediction")

if 'historical_predictions' not in st.session_state:
    st.session_state.historical_predictions = []
    st.session_state.game_times = []

win_prob_tab, teams_tab = st.tabs(["Win Probability", "Team Details"])

with win_prob_tab:
    chart_type = st.radio("Select Chart Type", ["Bar Chart", "Line Chart"], horizontal=True)
    chart_placeholder = st.empty()
    team_stats_placeholder = st.empty()

with teams_tab:
    team_details_placeholder = st.empty()

while True:
    data = fetch_data()
    summary_data = fetch_summary()
    if data:
        player_data = data.get("player_data", [])
        game_stats = data.get("game_stats", {})
        event_data = data.get("event_data", {})
        game_time = game_stats.get("gameTime", 0)

        for player in player_data:
            player['calculated_gold'] = calculate_gold(
                player["summonerName"],
                player["scores"]["creepScore"],
                player["scores"]["wardScore"],
                game_time,
                event_data
            )

            if not isinstance(player.get('items'), list):
                player['items'] = []

            if player['items']:
                player['items'] = sorted(player['items'],
                key=lambda x: x.get('slot', 0) if isinstance(x, dict) else 0)

        team_order_players = [p for p in player_data if p["team"] == "ORDER"]
        team_chaos_players = [p for p in player_data if p["team"] == "CHAOS"]

        team_order_gold = sum(p['calculated_gold'] for p in team_order_players)
        team_chaos_gold = sum(p['calculated_gold'] for p in team_chaos_players)

        model_input = prepare_model_input(player_data, team_order_gold, team_chaos_gold)
        game_time_minutes = game_time / 60
        predictions = predict_win_probability(model_input,game_time_minutes)

        with chart_placeholder.container():
            create_win_probability_chart(predictions, chart_type)

        with team_stats_placeholder.container():
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

        with team_details_placeholder.container():
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("### Team Order")
                for player in team_order_players:
                    display_player_card(player)

            with col2:
                st.markdown("### Team Chaos")
                for player in team_chaos_players:
                    display_player_card(player)

        summary_placeholder = st.empty()
        if summary_data:
            with summary_placeholder.container():  # Use the placeholder to overwrite
                st.markdown("### Game Summary")
                for key, value in summary_data.items():
                    st.markdown(f"**{key}:** {value}")

    else:
        st.write("Waiting for data...")
    time.sleep(5)