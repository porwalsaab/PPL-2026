import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
import random
import pytz
from twilio.rest import Client

# --- Configuration ---
PLAYERS = ["Porwal", "Baba", "Teja", "Sahil", "Bansal", "Naman"]
PLAYER_WHATSAPP = {
    "Porwal": "+917710012158",
    "Baba": "+917710033095",
    "Teja": "+917045688001",
    "Sahil": "+919560074024",
    "Bansal": "+917045688066",
    "Naman": "+918447959964",
}
DATA_FILE = "ipl_bets.json"
RESULTS_FILE = "match_results.json"
IST = pytz.timezone("Asia/Kolkata")

TWILIO_ACCOUNT_SID = st.secrets.get("TWILIO_ACCOUNT_SID", "your_twilio_account_sid")
TWILIO_AUTH_TOKEN = st.secrets.get("TWILIO_AUTH_TOKEN", "your_twilio_auth_token")
TWILIO_FROM_NUMBER = "whatsapp:+14155238886"

st.set_page_config(page_title="PoKaBaSaNaTe Premier League", layout="wide")

# --- Session State ---
if 'logged_in_player' not in st.session_state:
    st.session_state.logged_in_player = None

# --- Login ---
def login_via_whatsapp():
    whatsapp_input = st.text_input("Enter your WhatsApp number", placeholder="+91XXXXXXXXXX")
    if st.button("Login"):
        if whatsapp_input in PLAYER_WHATSAPP.values():
            player_name = next(name for name, num in PLAYER_WHATSAPP.items() if num == whatsapp_input)
            st.session_state.logged_in_player = player_name
            st.success(f"Welcome, {player_name}! 👋")
            st.rerun()
        else:
            st.error("Invalid WhatsApp number.")

# --- Data ---
def load_data(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {"bets": {}, "results": {}}

def save_data(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

# --- Schedule ---
@st.cache_data
def fetch_schedule():
    return [
        {"id": "M1", "match": "RCB vs SRH", "team_a": "RCB", "team_b": "SRH", "start_time": "2026-03-28 19:30:00"},
{"id": "M2", "match": "MI vs KKR", "team_a": "MI", "team_b": "KKR", "start_time": "2026-03-29 19:30:00"},
{"id": "M3", "match": "RR vs CSK", "team_a": "RR", "team_b": "CSK", "start_time": "2026-03-30 19:30:00"},
{"id": "M4", "match": "PBKS vs GT", "team_a": "PBKS", "team_b": "GT", "start_time": "2026-03-31 19:30:00"},
{"id": "M5", "match": "LSG vs DC", "team_a": "LSG", "team_b": "DC", "start_time": "2026-04-01 19:30:00"},
{"id": "M6", "match": "KKR vs SRH", "team_a": "KKR", "team_b": "SRH", "start_time": "2026-04-02 19:30:00"},
{"id": "M7", "match": "CSK vs PBKS", "team_a": "CSK", "team_b": "PBKS", "start_time": "2026-04-03 19:30:00"},
{"id": "M8", "match": "DC vs MI", "team_a": "DC", "team_b": "MI", "start_time": "2026-04-04 15:30:00"},
{"id": "M9", "match": "GT vs RR", "team_a": "GT", "team_b": "RR", "start_time": "2026-04-04 19:30:00"},
{"id": "M10", "match": "SRH vs LSG", "team_a": "SRH", "team_b": "LSG", "start_time": "2026-04-05 15:30:00"},
{"id": "M11", "match": "RCB vs CSK", "team_a": "RCB", "team_b": "CSK", "start_time": "2026-04-05 19:30:00"},
{"id": "M12", "match": "KKR vs PBKS", "team_a": "KKR", "team_b": "PBKS", "start_time": "2026-04-06 19:30:00"},
{"id": "M13", "match": "RR vs MI", "team_a": "RR", "team_b": "MI", "start_time": "2026-04-07 19:30:00"},
{"id": "M14", "match": "DC vs GT", "team_a": "DC", "team_b": "GT", "start_time": "2026-04-08 19:30:00"},
{"id": "M15", "match": "KKR vs LSG", "team_a": "KKR", "team_b": "LSG", "start_time": "2026-04-09 19:30:00"},
{"id": "M16", "match": "RR vs RCB", "team_a": "RR", "team_b": "RCB", "start_time": "2026-04-10 19:30:00"},
{"id": "M17", "match": "PBKS vs SRH", "team_a": "PBKS", "team_b": "SRH", "start_time": "2026-04-11 15:30:00"},
{"id": "M18", "match": "CSK vs DC", "team_a": "CSK", "team_b": "DC", "start_time": "2026-04-11 19:30:00"},
{"id": "M19", "match": "LSG vs GT", "team_a": "LSG", "team_b": "GT", "start_time": "2026-04-12 15:30:00"},
{"id": "M20", "match": "MI vs RCB", "team_a": "MI", "team_b": "RCB", "start_time": "2026-04-12 19:30:00"},
{"id": "M21", "match": "SRH vs RR", "team_a": "SRH", "team_b": "RR", "start_time": "2026-04-13 19:30:00"},
{"id": "M22", "match": "CSK vs KKR", "team_a": "CSK", "team_b": "KKR", "start_time": "2026-04-14 19:30:00"},
{"id": "M23", "match": "RCB vs LSG", "team_a": "RCB", "team_b": "LSG", "start_time": "2026-04-15 19:30:00"},
{"id": "M24", "match": "MI vs PBKS", "team_a": "MI", "team_b": "PBKS", "start_time": "2026-04-16 19:30:00"},
{"id": "M25", "match": "GT vs KKR", "team_a": "GT", "team_b": "KKR", "start_time": "2026-04-17 19:30:00"},
{"id": "M26", "match": "RCB vs DC", "team_a": "RCB", "team_b": "DC", "start_time": "2026-04-18 15:30:00"},
{"id": "M27", "match": "SRH vs CSK", "team_a": "SRH", "team_b": "CSK", "start_time": "2026-04-18 19:30:00"},
{"id": "M28", "match": "KKR vs RR", "team_a": "KKR", "team_b": "RR", "start_time": "2026-04-19 15:30:00"},
{"id": "M29", "match": "PBKS vs LSG", "team_a": "PBKS", "team_b": "LSG", "start_time": "2026-04-19 19:30:00"},
{"id": "M30", "match": "GT vs MI", "team_a": "GT", "team_b": "MI", "start_time": "2026-04-20 19:30:00"},
{"id": "M31", "match": "SRH vs DC", "team_a": "SRH", "team_b": "DC", "start_time": "2026-04-21 19:30:00"},
{"id": "M32", "match": "LSG vs RR", "team_a": "LSG", "team_b": "RR", "start_time": "2026-04-22 19:30:00"},
{"id": "M33", "match": "MI vs CSK", "team_a": "MI", "team_b": "CSK", "start_time": "2026-04-23 19:30:00"},
{"id": "M34", "match": "RCB vs GT", "team_a": "RCB", "team_b": "GT", "start_time": "2026-04-24 19:30:00"},
{"id": "M35", "match": "DC vs PBKS", "team_a": "DC", "team_b": "PBKS", "start_time": "2026-04-25 15:30:00"},
{"id": "M36", "match": "RR vs SRH", "team_a": "RR", "team_b": "SRH", "start_time": "2026-04-25 19:30:00"},
{"id": "M37", "match": "GT vs CSK", "team_a": "GT", "team_b": "CSK", "start_time": "2026-04-26 15:30:00"},
{"id": "M38", "match": "LSG vs KKR", "team_a": "LSG", "team_b": "KKR", "start_time": "2026-04-26 19:30:00"},
{"id": "M39", "match": "DC vs RCB", "team_a": "DC", "team_b": "RCB", "start_time": "2026-04-27 19:30:00"},
{"id": "M40", "match": "PBKS vs RR", "team_a": "PBKS", "team_b": "RR", "start_time": "2026-04-28 19:30:00"},
{"id": "M41", "match": "MI vs SRH", "team_a": "MI", "team_b": "SRH", "start_time": "2026-04-29 19:30:00"},
{"id": "M42", "match": "GT vs RCB", "team_a": "GT", "team_b": "RCB", "start_time": "2026-04-30 19:30:00"},
{"id": "M43", "match": "RR vs DC", "team_a": "RR", "team_b": "DC", "start_time": "2026-05-01 19:30:00"},
{"id": "M44", "match": "CSK vs MI", "team_a": "CSK", "team_b": "MI", "start_time": "2026-05-02 19:30:00"},
{"id": "M45", "match": "SRH vs KKR", "team_a": "SRH", "team_b": "KKR", "start_time": "2026-05-03 15:30:00"},
{"id": "M46", "match": "GT vs PBKS", "team_a": "GT", "team_b": "PBKS", "start_time": "2026-05-03 19:30:00"},
{"id": "M47", "match": "MI vs LSG", "team_a": "MI", "team_b": "LSG", "start_time": "2026-05-04 19:30:00"},
{"id": "M48", "match": "DC vs CSK", "team_a": "DC", "team_b": "CSK", "start_time": "2026-05-05 19:30:00"},
{"id": "M49", "match": "SRH vs PBKS", "team_a": "SRH", "team_b": "PBKS", "start_time": "2026-05-06 19:30:00"},
{"id": "M50", "match": "LSG vs RCB", "team_a": "LSG", "team_b": "RCB", "start_time": "2026-05-07 19:30:00"},
{"id": "M51", "match": "DC vs KKR", "team_a": "DC", "team_b": "KKR", "start_time": "2026-05-08 19:30:00"},
{"id": "M52", "match": "RR vs GT", "team_a": "RR", "team_b": "GT", "start_time": "2026-05-09 19:30:00"},
{"id": "M53", "match": "CSK vs LSG", "team_a": "CSK", "team_b": "LSG", "start_time": "2026-05-10 15:30:00"},
{"id": "M54", "match": "RCB vs MI", "team_a": "RCB", "team_b": "MI", "start_time": "2026-05-10 19:30:00"},
{"id": "M55", "match": "PBKS vs DC", "team_a": "PBKS", "team_b": "DC", "start_time": "2026-05-11 19:30:00"},
{"id": "M56", "match": "GT vs SRH", "team_a": "GT", "team_b": "SRH", "start_time": "2026-05-12 19:30:00"},
{"id": "M57", "match": "RCB vs KKR", "team_a": "RCB", "team_b": "KKR", "start_time": "2026-05-13 19:30:00"},
{"id": "M58", "match": "PBKS vs MI", "team_a": "PBKS", "team_b": "MI", "start_time": "2026-05-14 19:30:00"},
{"id": "M59", "match": "LSG vs CSK", "team_a": "LSG", "team_b": "CSK", "start_time": "2026-05-15 19:30:00"},
{"id": "M60", "match": "KKR vs GT", "team_a": "KKR", "team_b": "GT", "start_time": "2026-05-16 19:30:00"},
{"id": "M61", "match": "PBKS vs RCB", "team_a": "PBKS", "team_b": "RCB", "start_time": "2026-05-17 15:30:00"},
{"id": "M62", "match": "DC vs RR", "team_a": "DC", "team_b": "RR", "start_time": "2026-05-17 19:30:00"},
{"id": "M63", "match": "CSK vs SRH", "team_a": "CSK", "team_b": "SRH", "start_time": "2026-05-18 19:30:00"},
{"id": "M64", "match": "RR vs LSG", "team_a": "RR", "team_b": "LSG", "start_time": "2026-05-19 19:30:00"},
{"id": "M65", "match": "KKR vs MI", "team_a": "KKR", "team_b": "MI", "start_time": "2026-05-20 19:30:00"},
{"id": "M66", "match": "CSK vs GT", "team_a": "CSK", "team_b": "GT", "start_time": "2026-05-21 19:30:00"},
{"id": "M67", "match": "SRH vs RCB", "team_a": "SRH", "team_b": "RCB", "start_time": "2026-05-22 19:30:00"},
{"id": "M68", "match": "LSG vs PBKS", "team_a": "LSG", "team_b": "PBKS", "start_time": "2026-05-23 19:30:00"},
{"id": "M69", "match": "MI vs RR", "team_a": "MI", "team_b": "RR", "start_time": "2026-05-24 15:30:00"},
{"id": "M70", "match": "KKR vs DC", "team_a": "KKR", "team_b": "DC", "start_time": "2026-05-24 19:30:00"},
    ]

# --- Logic ---
def handle_auto_bets(data, match, m_id):
    if m_id not in data["bets"]:
        data["bets"][m_id] = {}
    for player in PLAYERS:
        if player not in data["bets"][m_id]:
            data["bets"][m_id][player] = random.choice([match["team_a"], match["team_b"]])
    save_data(data, DATA_FILE)

# --- App ---
st.title("🏆 PoKaBaSaNaTe Premier League 2026")

schedule = fetch_schedule()
data = load_data(DATA_FILE)
current_time_ist = datetime.now(IST)

# --- Login ---
if st.session_state.logged_in_player is None:
    st.header("🔐 Login Required")
    login_via_whatsapp()
else:
    st.sidebar.success(f"Logged in as: {st.session_state.logged_in_player}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in_player = None
        st.rerun()

    tab1, tab2 = st.tabs(["Place Bets", "Leaderboard"])

    # =========================
    # ✅ PLACE BETS TAB (UPDATED)
    # =========================
    with tab1:
        st.header("Place Your Bet")

        # ✅ UPDATED DROPDOWN (Match ID + Name)
        match_options = {f"{m['id']} {m['match']}": m for m in schedule}
        selected_match_str = st.selectbox("Select Match", list(match_options.keys()))
        selected_match = match_options[selected_match_str]

        m_id = selected_match["id"]
        player = st.session_state.logged_in_player

        match_start = IST.localize(datetime.strptime(selected_match["start_time"], "%Y-%m-%d %H:%M:%S"))
        cutoff_time = match_start - timedelta(seconds=10)
        is_past_cutoff = current_time_ist >= cutoff_time

        if is_past_cutoff:
            handle_auto_bets(data, selected_match, m_id)
            st.error("Betting closed!")
        else:
            st.write(f"**{selected_match['team_a']} vs {selected_match['team_b']}**")

            if m_id not in data["bets"]:
                data["bets"][m_id] = {}

            current_bet = data["bets"][m_id].get(player, selected_match["team_a"])

            new_bet = st.radio(
                "Your Bet:",
                [selected_match["team_a"], selected_match["team_b"]],
                index=0 if current_bet == selected_match["team_a"] else 1
            )

            if st.button("Save Bet"):
                data["bets"][m_id][player] = new_bet
                save_data(data, DATA_FILE)
                st.success("Bet saved!")

        # =========================
        # ✅ SHOW ALL PLAYER BETS
        # =========================
        st.subheader("📊 All Players Bets")

        match_bets = data["bets"].get(m_id, {})

        if match_bets:
            bets_df = pd.DataFrame({
                "Player": PLAYERS,
                "Bet": [match_bets.get(p, "Not Placed") for p in PLAYERS]
            })
            st.table(bets_df)
        else:
            st.info("No bets placed yet.")

    # --- Leaderboard (basic) ---
    with tab2:
        st.header("Leaderboard (Coming Soon)")
