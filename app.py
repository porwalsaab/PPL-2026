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

# Twilio (set in Streamlit secrets)
TWILIO_ACCOUNT_SID = st.secrets.get("TWILIO_ACCOUNT_SID", "your_twilio_account_sid")
TWILIO_AUTH_TOKEN = st.secrets.get("TWILIO_AUTH_TOKEN", "your_twilio_auth_token")
TWILIO_FROM_NUMBER = "whatsapp:+14155238886"

st.set_page_config(page_title="PoKaBaSaNaTe Premier League", layout="wide")

# --- Custom CSS for improved theming ---
st.markdown("""
<style>
[data-testid="stAppViewContainer"] {background-color: #1D3D8D; color: #FFFFFF;}
h1, h2, h3 {color: #FFD700 !important;}
.stTabs [data-baseweb="tab-list"] button {color: #FFFFFF;}
.stTabs [aria-selected="true"] {color: #FFD700 !important; border-bottom-color: #FFD700 !important;}
div[data-testid="stRadio"] label {color: #FFFFFF !important;}
.stButton>button {background-color: #FFD700; color: #1D3D8D; border: none; font-weight: 800;}
.stButton>button:hover {background-color: #5091CD; color: #FFFFFF;}
[data-testid="stExpander"] {background-color: #5091CD; border: 1px solid #FFD700; border-radius: 8px;}
[data-testid="stExpander"] p {color: #FFFFFF; font-weight: bold;}
th, td {color: #FFFFFF; background-color: #1D3D8D;}
.metric-card {background-color: #5091CD; padding: 1rem; border-radius: 10px; border: 2px solid #FFD700; text-align: center;}
</style>
""", unsafe_allow_html=True)

# --- Session State for Login ---
if 'logged_in_player' not in st.session_state:
    st.session_state.logged_in_player = None
if 'results_shown' not in st.session_state:
    st.session_state.results_shown = False

# --- Login Function ---
def login_via_whatsapp():
    whatsapp_input = st.text_input("Enter your WhatsApp number", placeholder="+91XXXXXXXXXX")
    if st.button("Login"):
        if whatsapp_input in PLAYER_WHATSAPP.values():
            player_name = next(name for name, num in PLAYER_WHATSAPP.items() if num == whatsapp_input)
            st.session_state.logged_in_player = player_name
            st.success(f"Welcome, {player_name}! 👋")
            st.rerun()
        else:
            st.error("Invalid WhatsApp number. Please check and try again.")

# --- Data Management ---
def load_data(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {} if filename == "match_results.json" else {"bets": {}, "results": {}}

def save_data(data, filename):
    os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else '.', exist_ok=True)
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

# --- Schedule ---
@st.cache_data
def fetch_schedule():
    return [
        {"id": "M1", "match": "RCB vs SRH", "team_a": "RCB", "team_b": "SRH", "start_time": "2026-03-28 19:30:00"},
        {"id": "M2", "match": "MI vs KKR", "team_a": "MI", "team_b": "KKR", "start_time": "2026-03-29 19:30:00"},
        {"id": "M3", "match": "RR vs CSK", "team_a": "RR", "team_b": "CSK", "start_time": "2026-03-30 19:30:00"},
    ]

# --- Core Logic (unchanged except rounding) ---
def calculate_match_points(match_bets, winner):
    points = {p: 0 for p in PLAYERS}
    winners = [p for p in PLAYERS if match_bets.get(p) == winner]
    losers = [p for p in PLAYERS if match_bets.get(p) and match_bets.get(p) != winner]
    if len(winners) > 0 and len(losers) > 0:
        total_lost = len(losers) * 100
        gain_per_winner = total_lost / len(winners)
        for w in winners:
            points[w] = round(gain_per_winner)
        for l in losers:
            points[l] = -100
    return points

def calculate_leaderboard(data, schedule):
    scores = {player: 0 for player in PLAYERS}
    for match in schedule:
        m_id = match["id"]
        if m_id in data["results"] and m_id in data["bets"]:
            match_points = calculate_match_points(data["bets"][m_id], data["results"][m_id])
            for p, pts in match_points.items():
                scores[p] += pts
    return {k: round(v) for k, v in scores.items()}

def calculate_cumulative_scores(data, schedule):
    history_data = [{"Match": "Start", **{p: 0 for p in PLAYERS}}]
    cumulative = {p: 0 for p in PLAYERS}
    for match in schedule:
        m_id = match["id"]
        if m_id in data["results"] and m_id in data["bets"]:
            match_points = calculate_match_points(data["bets"][m_id], data["results"][m_id])
            for p in PLAYERS:
                cumulative[p] += match_points.get(p, 0)
            history_data.append({"Match": match["match"], **{k: round(v) for k, v in cumulative.items()}})
    df = pd.DataFrame(history_data)
    df.set_index("Match", inplace=True)
    return df

def handle_auto_bets(data, match, m_id):
    if m_id not in data["bets"]:
        data["bets"][m_id] = {}
    changes_made = False
    for player in PLAYERS:
        if player not in data["bets"][m_id]:
            auto_team = random.choice([match["team_a"], match["team_b"]])
            data["bets"][m_id][player] = auto_team
            changes_made = True
    if changes_made:
        save_data(data, DATA_FILE)

def send_whatsapp_reminders(missing_players, match_name, time_remaining):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    for player in missing_players:
        msg_body = f"🏆 PoKaBaSaNaTe Premier League 2026 Alert!\nHey {player}, you haven\'t placed your bet for {match_name} yet!\nYou have {time_remaining} left before you get auto-assigned a team."
        try:
            client.messages.create(from_=TWILIO_FROM_NUMBER, body=msg_body, to=PLAYER_WHATSAPP[player])
        except Exception as e:
            st.error(f"Failed to send to {player}: {e}")

# --- Main App ---
st.title("🏆 PoKaBaSaNaTe Premier League 2026")

schedule = fetch_schedule()
data = load_data(DATA_FILE)
results_data = load_data(RESULTS_FILE)  # Separate results storage
current_time_ist = datetime.now(IST)

# --- Login Check ---
if st.session_state.logged_in_player is None:
    st.header("🔐 Login Required")
    login_via_whatsapp()
else:
    st.sidebar.success(f"Logged in as: **{st.session_state.logged_in_player}** 👤")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in_player = None
        st.rerun()

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["Place Bets", "Update Results", "Leaderboard", "Match History", "Rules", "Matches"])

    # --- Place Bets (Only own bet) ---
    with tab1:
        if st.session_state.logged_in_player:
            st.header("Place Your Bet")
            selected_match_str = st.selectbox("Select Match", [m["match"] for m in schedule])
            selected_match = next(m for m in schedule if m["match"] == selected_match_str)
            m_id = selected_match["id"]

            match_start_naive = datetime.strptime(selected_match["start_time"], "%Y-%m-%d %H:%M:%S")
            match_start = IST.localize(match_start_naive)
            cutoff_time = match_start - timedelta(seconds=10)
            is_past_cutoff = current_time_ist >= cutoff_time

            player = st.session_state.logged_in_player

            if is_past_cutoff:
                handle_auto_bets(data, selected_match, m_id)
                st.error(f"Betting for {selected_match['match']} is closed!")
                st.info("Auto-assigned if no bet placed.")
                current_bet = data['bets'].get(m_id, {}).get(player, "Auto-assigned")
                st.metric("Your Bet", current_bet)
            elif m_id in data["results"]:
                st.warning("Match already decided!")
                current_bet = data['bets'].get(m_id, {}).get(player)
                st.metric("Your Bet", current_bet or "No bet")
            else:
                st.write(f"**{selected_match['team_a']}** vs **{selected_match['team_b']}**")
                st.caption(f"Closes: {cutoff_time.strftime('%d %b %Y, %I:%M:%S %p')} IST")

                if m_id not in data["bets"]:
                    data["bets"][m_id] = {}

                current_bet = data["bets"][m_id].get(player, selected_match["team_a"])
                new_bet = st.radio("Your Bet:", [selected_match["team_a"], selected_match["team_b"]], 
                                 index=0 if current_bet == selected_match["team_a"] else 1, 
                                 key=f"bet_{m_id}_{player}")

                if st.button("Save My Bet", key=f"save_{m_id}"):
                    data["bets"][m_id][player] = new_bet
                    save_data(data, DATA_FILE)
                    st.success("Bet saved! ✅")

        else:
            st.warning("Please login to place bets.")

    # --- Update Results (Porwal only) ---
    with tab2:
        st.header("Update Match Results")
        if st.session_state.logged_in_player == "Porwal":
            res_match_str = st.selectbox("Select Match to Resolve", [m["match"] for m in schedule], key="res_match")
            res_match = next(m for m in schedule if m["match"] == res_match_str)
            r_id = res_match["id"]

            if r_id not in data["bets"]:
                st.info("No bets for this match yet.")
            else:
                with st.form(f"res_form_{r_id}"):
                    winner = st.radio("Winner:", [res_match["team_a"], res_match["team_b"]])
                    if st.form_submit_button("Confirm Result"):
                        data["results"][r_id] = winner
                        results_data[r_id] = {
                            "winner": winner,
                            "timestamp": current_time_ist.isoformat(),
                            "updated_by": "Porwal"
                        }
                        save_data(data, DATA_FILE)
                        save_data(results_data, RESULTS_FILE)
                        st.success(f"{winner} won! Saved. 🎉")
        else:
            st.warning("❌ Access restricted to Porwal only.")

    # --- Enhanced Leaderboard ---
    with tab3:
        st.header("🏆 PPL Leaderboard")
        scores = calculate_leaderboard(data, schedule)
        df_scores = pd.DataFrame(list(scores.items()), columns=["Player", "Points"]).sort_values(by="Points", ascending=False)
        df_scores.index = range(1, len(df_scores) + 1)
        df_scores["Points"] = df_scores["Points"].apply(lambda x: f"{x:+d}")

        st.subheader("📈 Season Progress")
        cum_df = calculate_cumulative_scores(data, schedule)
        if len(cum_df) > 1:
            st.line_chart(cum_df)
        else:
            st.info("📊 Chart appears after first match result.")

        st.subheader("🥇 Current Standings")
        for idx, row in df_scores.iterrows():
            rank_emoji = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else "🏅"
            col1, col2, col3 = st.columns([1, 3, 2])
            with col1:
                st.markdown(f"**{rank_emoji} #{idx}**")
            with col2:
                st.markdown(f"**{row['Player']}**")
            with col3:
                st.markdown(row["Points"])

    # --- Match History (unchanged except rounding) ---
    with tab4:
        st.header("📜 Match History")
        completed_matches = [m for m in schedule if m["id"] in data["results"]]
        if not completed_matches:
            st.info("No completed matches yet.")
        else:
            for match in reversed(completed_matches):
                m_id = match["id"]
                winner = data["results"][m_id]
                match_bets = data["bets"].get(m_id, {})
                match_points = calculate_match_points(match_bets, winner)

                with st.expander(f"✅ {match['match']} | Winner: **{winner}**"):
                    history_df = pd.DataFrame({
                        "Player": PLAYERS,
                        "Bet": [match_bets.get(p, "Auto") for p in PLAYERS],
                        "Points": [match_points.get(p, 0) for p in PLAYERS]
                    })
                    history_df["Points"] = history_df["Points"].apply(lambda x: f"{x:+d}")
                    st.table(history_df)

    # --- Rules (unchanged) ---
    with tab5:
        st.header("📘 Rules")
        st.markdown("""
        - **Players**: Porwal, Baba, Teja, Sahil, Bansal, Naman
        - **Betting**: Change anytime before 10s cutoff
        - **Auto-bet**: Random if no bet
        - **Scoring**: Losers -100, split among winners
        - **Fun only!** No money.
        """)

    # --- Matches ---
    with tab6:
        st.header("📅 Fixtures")
        matches_df = pd.DataFrame([
            {
                "ID": m["id"],
                "Match": m["match"],
                "Team A": m["team_a"],
                "Team B": m["team_b"],
                "Start (IST)": datetime.strptime(m["start_time"], "%Y-%m-%d %H:%M:%S").strftime("%d %b, %I:%M %p")
            } for m in schedule
        ])
        st.table(matches_df)
