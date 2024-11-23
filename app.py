import streamlit as st
import requests

# Public ngrok URL
data_url = "https://92e9-202-166-153-36.ngrok-free.app/data"

def fetch_data():
    """Fetch data from the ngrok-exposed Flask endpoint."""
    try:
        response = requests.get(data_url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return {}

st.title("League of Legends Data")

# Fetch and display data
data = fetch_data()

if data:
    st.write("### Player Data")
    st.json(data.get("player_data", {}))

    st.write("### Game Stats")
    st.json(data.get("game_stats", {}))

    st.write("### Event Data")
    st.json(data.get("event_data", {}))
else:
    st.write("No data available.")
