import streamlit as st
import firebase_admin
from firebase_admin import credentials, db
import pandas as pd
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="DHT11 Dashboard",
    page_icon="🌡️",
    layout="wide"
)

# ── Session state (login) ─────────────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

def login():
    st.title("🔐 DHT11 Dashboard Login")
    user = st.text_input("Username")
    pwd  = st.text_input("Password", type="password")
    if st.button("Login"):
        if (user == st.secrets["auth"]["username"] and
                pwd == st.secrets["auth"]["password"]):
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Invalid credentials. Please try again.")

if not st.session_state.logged_in:
    login()
    st.stop()

# ── Logout button ─────────────────────────────────────────────────────────────
col1, col2 = st.columns([8, 1])
with col2:
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🌡️ DHT11 Monitoring Dashboard")
st_autorefresh(interval=10000, key="autorefresh")

# ── Firebase init ─────────────────────────────────────────────────────────────
if not firebase_admin._apps:
    firebase_config = dict(st.secrets["firebase"])
    cred = credentials.Certificate(firebase_config)
    firebase_admin.initialize_app(cred, {
        "databaseURL": firebase_config["databaseURL"]
    })

# ── Load data ─────────────────────────────────────────────────────────────────
@st.cache_data(ttl=5)
def load_data():
    ref = db.reference("dht_history")
    return ref.get()

data = load_data()
if not data:
    st.warning("No data found in Firebase.")
    st.stop()

records = [
    {"time": k, "temperature": v.get("temperature"), "humidity": v.get("humidity")}
    for k, v in data.items() if isinstance(v, dict)
]

df = pd.DataFrame(records)
df["time"] = pd.to_datetime(df["time"], format="%Y-%m-%d_%H:%M:%S")
df = df.sort_values("time")

# ── Live metrics ──────────────────────────────────────────────────────────────
latest = df.iloc[-1]
col1, col2 = st.columns(2)
col1.metric("🌡️ Temperature", f"{latest['temperature']} °C")
col2.metric("💧 Humidity",    f"{latest['humidity']} %")

# ── Sidebar filter ────────────────────────────────────────────────────────────
st.sidebar.header("📅 Date Filter")
start = st.sidebar.date_input("Start", df["time"].min().date())
end   = st.sidebar.date_input("End",   df["time"].max().date())
df_filtered = df[(df["time"].dt.date >= start) & (df["time"].dt.date <= end)]

# ── Charts ────────────────────────────────────────────────────────────────────
fig1 = px.line(df_filtered, x="time", y="temperature",
               markers=True, title="Temperature Over Time")
fig1.update_layout(template="plotly_dark")
st.plotly_chart(fig1, use_container_width=True)

fig2 = px.line(df_filtered, x="time", y="humidity",
               markers=True, title="Humidity Over Time")
fig2.update_layout(template="plotly_dark")
st.plotly_chart(fig2, use_container_width=True)

# ── Table ─────────────────────────────────────────────────────────────────────
st.dataframe(df_filtered[["time", "temperature", "humidity"]],
             use_container_width=True)

# ── CSV export ────────────────────────────────────────────────────────────────
export = df_filtered.copy()
export["time"] = export["time"].dt.strftime("%Y-%m-%d %H:%M:%S")
csv = export[["time", "temperature", "humidity"]].to_csv(index=False, sep=";")
st.download_button("⬇ Download CSV", csv, "dht_data.csv", "text/csv")
st.caption("🔄 Auto-refreshes every 10 seconds")
