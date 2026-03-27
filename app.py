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
DATA_FILE = "ipl_bets.json"
IST = pytz.timezone("Asia/Kolkata")

# Use Streamlit secrets in cloud; fall back to placeholders locally
TWILIO_ACCOUNT_SID = st.secrets.get("TWILIO_ACCOUNT_SID", "your_twilio_account_sid")
TWILIO_AUTH_TOKEN = st.secrets.get("TWILIO_AUTH_TOKEN", "your_twilio_auth_token")
TWILIO_FROM_NUMBER = "whatsapp:+14155238886"  # Twilio sandbox default

PLAYER_NUMBERS = {
    "Porwal": "whatsapp:+917710012158",
    "Baba": "whatsapp:+917710033095",
    "Teja": "whatsapp:+917045688001",
    "Sahil": "whatsapp:+919560074024",
    "Bansal": "whatsapp:+917045688066",
    "Naman": "whatsapp:+918447959964",
}

st.set_page_config(page_title="PoKaBaSaNaTe Premier League", layout="wide")

# --- IPL UI Theming ---
st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background-color: #1D3D8D;
        color: #FFFFFF;
    }
    h1, h2, h3, h4 {
        color: #FFD700 !important;
    }
    .stTabs [data-baseweb="tab-list"] button {
        color: #FFFFFF;
    }
    .stTabs [aria-selected="true"] {
        color: #FFD700 !important;
        border-bottom-color: #FFD700 !important;
    }
    div[data-testid="stRadio"] label {
        color: #FFFFFF !important;
    }
    .stButton>button {
        background-color: #FFD700;
        color: #1D3D8D;
        border: none;
        font-weight: 800;
    }
    .stButton>button:hover {
        background-color: #5091CD;
        color: #FFFFFF;
    }
    [data-testid="stExpander"] {
        background-color: #5091CD;
        border: 1px solid #FFD700;
        border-radius: 8px;
    }
    [data-testid="stExpander"] p {
        color: #FFFFFF;
        font-weight: bold;
    }
    th, td {
        color: #FFFFFF;
        background-color: #1D3D8D;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Data Management ---
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"bets": {}, "results": {}}


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


# --- Schedule (can be extended easily) ---
@st.cache_data
def fetch_schedule():
    return [
        {
            "id": "M1",
            "match": "RCB vs SRH",
            "team_a": "RCB",
            "team_b": "SRH",
            "start_time": "2026-03-28 19:30:00",
        },
        {
            "id": "M2",
            "match": "MI vs KKR",
            "team_a": "MI",
            "team_b": "KKR",
            "start_time": "2026-03-29 19:30:00",
        },
        {
            "id": "M3",
            "match": "RR vs CSK",
            "team_a": "RR",
            "team_b": "CSK",
            "start_time": "2026-03-30 19:30:00",
        },
    ]


# --- Core Logic ---
def calculate_match_points(match_bets, winner):
    points = {p: 0 for p in PLAYERS}
    winners = [p for p in PLAYERS if match_bets.get(p) == winner]
    losers = [
        p for p in PLAYERS if match_bets.get(p) and match_bets.get(p) != winner
    ]

    if len(winners) > 0 and len(losers) > 0:
        total_lost = len(losers) * 100
        gain_per_winner = total_lost / len(winners)
        for w in winners:
            points[w] = gain_per_winner
        for l in losers:
            points[l] = -100
    return points


def calculate_leaderboard(data, schedule):
    scores = {player: 0 for player in PLAYERS}
    for match in schedule:
        m_id = match["id"]
        if m_id in data["results"] and m_id in data["bets"]:
            match_points = calculate_match_points(
                data["bets"][m_id], data["results"][m_id]
            )
            for p, pts in match_points.items():
                scores[p] += pts
    return scores


def calculate_cumulative_scores(data, schedule):
    history_data = [{"Match": "Start", **{p: 0 for p in PLAYERS}}]
    cumulative = {p: 0 for p in PLAYERS}
    for match in schedule:
        m_id = match["id"]
        if m_id in data["results"] and m_id in data["bets"]:
            match_points = calculate_match_points(
                data["bets"][m_id], data["results"][m_id]
            )
            for p in PLAYERS:
                cumulative[p] += match_points.get(p, 0)
            history_data.append({"Match": match["match"], **cumulative})
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
        save_data(data)


def send_whatsapp_reminders(missing_players, match_name, time_remaining):
    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    for player in missing_players:
        if player in PLAYER_NUMBERS:
            msg_body = (
                "🏆 *PoKaBaSaNaTe Premier League 2026 Alert!*\n"
                f"Hey {player}, you haven't placed your bet for *{match_name}* yet!\n"
                f"You have {time_remaining} left before you get auto-assigned a team."
            )
            try:
                client.messages.create(
                    from_=TWILIO_FROM_NUMBER,
                    body=msg_body,
                    to=PLAYER_NUMBERS[player],
                )
            except Exception as e:
                st.error(f"Failed to send to {player}: {e}")


# --- UI Setup ---
st.title("🏆 PoKaBaSaNaTe Premier League 2026")

schedule = fetch_schedule()
data = load_data()
current_time_ist = datetime.now(IST)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
    [
        "Place Bets",
        "Update Results",
        "Leaderboard",
        "Match History",
        "Rules",
        "Matches",
    ]
)

# --- Place Bets ---
with tab1:
    st.header("Place Your Bets")

    selected_match_str = st.selectbox(
        "Select Match", [m["match"] for m in schedule]
    )
    selected_match = next(m for m in schedule if m["match"] == selected_match_str)
    m_id = selected_match["id"]

    match_start_naive = datetime.strptime(
        selected_match["start_time"], "%Y-%m-%d %H:%M:%S"
    )
    match_start = IST.localize(match_start_naive)
    cutoff_time = match_start - timedelta(seconds=10)
    is_past_cutoff = current_time_ist >= cutoff_time

    if is_past_cutoff:
        handle_auto_bets(data, selected_match, m_id)
        st.error(
            f"Betting for {selected_match['match']} is closed! The 10-second cutoff has passed."
        )
        st.info(
            "Any players who did not bet have been auto-assigned a random team."
        )
        st.write("### Locked Bets")
        for p in PLAYERS:
            st.write(f"**{p}**: {data['bets'][m_id].get(p)}")

    elif m_id in data["results"]:
        st.warning("Match already decided!")

    else:
        st.write(
            f"**{selected_match['team_a']}** vs **{selected_match['team_b']}**"
        )
        st.caption(
            f"Match Start (IST): {match_start.strftime('%d %b %Y, %I:%M %p')}"
        )
        st.caption(
            f"Betting Closes (IST): {cutoff_time.strftime('%d %b %Y, %I:%M:%S %p')}"
        )

        if m_id not in data["bets"]:
            data["bets"][m_id] = {}

        # Live view of current bets
        current_bets = data["bets"][m_id]
        team_a = selected_match["team_a"]
        team_b = selected_match["team_b"]
        team_a_players = [p for p, t in current_bets.items() if t == team_a]
        team_b_players = [p for p, t in current_bets.items() if t == team_b]
        no_bet_players = [p for p in PLAYERS if p not in current_bets]

        st.subheader("Current Bets")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(f"**{team_a}**")
            if team_a_players:
                st.write(", ".join(team_a_players))
            else:
                st.write("No bets yet")
        with col2:
            st.markdown(f"**{team_b}**")
            if team_b_players:
                st.write(", ".join(team_b_players))
            else:
                st.write("No bets yet")
        with col3:
            st.markdown("**No bet yet**")
            if no_bet_players:
                st.write(", ".join(no_bet_players))
            else:
                st.write("Everyone has bet")

        # Reminders
        missing_players = [p for p in PLAYERS if p not in current_bets]
        if missing_players:
            st.warning(f"Pending bets from: {', '.join(missing_players)}")
            time_left = cutoff_time - current_time_ist
            if time_left.total_seconds() > 0:
                hours, remainder = divmod(int(time_left.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                time_left_str = (
                    f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"
                )
            else:
                time_left_str = "0s"

            if st.button("📲 Send WhatsApp Reminders to Missing Players"):
                if TWILIO_ACCOUNT_SID == "your_twilio_account_sid":
                    st.error(
                        "Please set Twilio credentials in Streamlit secrets before using reminders."
                    )
                else:
                    send_whatsapp_reminders(
                        missing_players, selected_match["match"], time_left_str
                    )
                    st.success("Reminders sent successfully!")

        # Betting form – players can change bet any number of times before cutoff
        with st.form(f"bet_form_{m_id}"):
            cols = st.columns(3)
            for i, player in enumerate(PLAYERS):
                col = cols[i % 3]
                current_bet = data["bets"][m_id].get(player, team_a)
                data["bets"][m_id][player] = col.radio(
                    f"{player}'s Bet",
                    [team_a, team_b],
                    index=0 if current_bet == team_a else 1,
                    key=f"{m_id}_{player}",
                )
            if st.form_submit_button("Save Bets"):
                save_data(data)
                st.success("Bets saved. You can still change them until betting closes.")


# --- Update Results ---
with tab2:
    st.header("Update Match Results")

    res_match_str = st.selectbox(
        "Select Match to Resolve", [m["match"] for m in schedule], key="res_match"
    )
    res_match = next(m for m in schedule if m["match"] == res_match_str)
    r_id = res_match["id"]

    if r_id not in data["bets"]:
        st.info("No bets placed for this match yet.")
    else:
        with st.form(f"res_form_{r_id}"):
            winner = st.radio(
                "Who won the match?", [res_match["team_a"], res_match["team_b"]]
            )
            if st.form_submit_button("Confirm Result"):
                data["results"][r_id] = winner
                save_data(data)
                st.success(f"Result saved! {winner} won.")


# --- Leaderboard ---
with tab3:
    st.header("🏆 PPL Leaderboard")

    scores = calculate_leaderboard(data, schedule)
    df_scores = pd.DataFrame(
        list(scores.items()), columns=["Player", "Total Points"]
    ).sort_values(by="Total Points", ascending=False)
    df_scores.index = range(1, len(df_scores) + 1)

    st.subheader("📈 Season Progress Tracker")
    cum_df = calculate_cumulative_scores(data, schedule)
    if cum_df.shape[0] > 1:
        st.line_chart(cum_df)
    else:
        st.info("Once at least one match is completed, the progress chart will appear here.")

    st.subheader("📋 Current Standings")
    st.table(df_scores)


# --- Match History ---
with tab4:
    st.header("📜 Match History")

    completed_matches = [m for m in schedule if m["id"] in data["results"]]
    if not completed_matches:
        st.info("No matches have been completed yet.")
    else:
        for match in reversed(completed_matches):
            m_id = match["id"]
            winner = data["results"][m_id]
            match_bets = data["bets"].get(m_id, {})
            match_points = calculate_match_points(match_bets, winner)

            with st.expander(f"✅ {match['match']} | Winner: {winner}"):
                history_df = pd.DataFrame(
                    {
                        "Player": PLAYERS,
                        "Bet Placed": [
                            match_bets.get(p, "Auto-Assigned (No Bet)")
                            for p in PLAYERS
                        ],
                        "Points Gained/Lost": [
                            match_points.get(p, 0) for p in PLAYERS
                        ],
                    }
                )
                history_df["Points Gained/Lost"] = history_df[
                    "Points Gained/Lost"
                ].apply(lambda x: f"+{int(x)}" if x > 0 else str(int(x)))
                st.table(history_df)


# --- Rules ---
with tab5:
    st.header("📘 PPL 2026 Rules")

    st.subheader("1. Players")
    st.markdown(
        "- Fixed players: **Porwal**, **Baba**, **Teja**, **Sahil**, **Bansal**, **Naman**.\n"
        "- Everyone starts from 0 points."
    )

    st.subheader("2. Bets and timing")
    st.markdown(
        "- You can change your bet any number of times before betting closes.\n"
        "- Betting closes **10 seconds before** the official start time of the match.\n"
        "- After betting is closed, no one can edit their bet."
    )

    st.subheader("3. Auto-assigned bets")
    st.markdown(
        "- If a player has **not placed any bet** when betting closes, the app automatically assigns a random team (one of the two playing teams).\n"
        "- Auto-assigned bets are treated exactly like normal bets for scoring."
    )

    st.subheader("4. Visibility of bets")
    st.markdown(
        "- Before the cutoff, players can see **who is betting on which team** for the selected match.\n"
        "- After the cutoff, all bets are locked and still visible to everyone."
    )

    st.subheader("5. Scoring per match")
    st.markdown(
        "- Each **losing** player loses 100 points.\n"
        "- The total points lost (100 × number of losers) are split equally among all **winners**.\n"
        "- If everyone picks the same team, no one wins or loses anything for that match."
    )

    st.subheader("6. Leaderboard and history")
    st.markdown(
        "- The **Leaderboard** tab shows each player's **total points** across all matches.\n"
        "- The **Season Progress** chart shows how each player’s total points change match by match.\n"
        "- The **Match History** tab shows, for every completed match:\n"
        "  - Which team each player bet on.\n"
        "  - How many points they won or lost in that specific match."
    )

    st.subheader("7. Fun and fairness")
    st.markdown(
        "- This app is for **fun only** – no real money.\n"
        "- Use your WhatsApp group *PoKaBaSaNaTe* to coordinate and enjoy the PPL 2026 season!"
    )


# --- Matches (Fixtures) ---
with tab6:
    st.header("📅 Upcoming IPL Fixtures")

    if not schedule:
        st.info("No fixtures available right now.")
    else:
        matches_df = pd.DataFrame(
            [
                {
                    "Match ID": m["id"],
                    "Match": m["match"],
                    "Team A": m["team_a"],
                    "Team B": m["team_b"],
                    "Start Time (IST)": datetime.strptime(
                        m["start_time"], "%Y-%m-%d %H:%M:%S"
                    ).strftime("%d %b %Y, %I:%M %p"),
                }
                for m in schedule
            ]
        )
        st.table(matches_df)
        st.caption(
            "All times are in IST. These fixtures are used for betting, scoring, and history in this app."
        )
