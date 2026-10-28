import streamlit as st
import pandas as pd
import requests
import plotly.express as px
import time

st.set_page_config(page_title="Live Weather (Denver)", page_icon="🌡️", layout="wide")
# Disable fade/transition so charts don't blink between reruns
st.markdown("""
    <style>
      [data-testid="stPlotlyChart"], .stPlotlyChart, .stElementContainer {
        transition: none !important;
        opacity: 1 !important;
      }
    </style>
""", unsafe_allow_html=True)

st.title("🌡️ Live Weather Demo (Open-Meteo)")
st.caption("Current Denver temperature and wind, cached and auto-refreshed, with a session history.")

# --- Config ---
lat, lon = 39.7392, -104.9903  # Denver
wurl = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,wind_speed_10m"
hurl = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&hourly=temperature_2m&past_days=1&forecast_days=1&timezone=America/Denver")

# Fallback so the page still renders if the API is down
SAMPLE_DF = pd.DataFrame([{"time": pd.Timestamp.now().floor("15min"), "temperature": 12.0, "wind": 8.0}])


# --- Fetch (cached) ---
@st.cache_data(ttl=600, show_spinner=False)  # Cache for 10 minutes
def get_weather():
    r = requests.get(wurl, timeout=10); r.raise_for_status()
    j = r.json()["current"]
    return pd.DataFrame([{"time": pd.to_datetime(j["time"]),
                          "temperature": j["temperature_2m"],
                          "wind": j["wind_speed_10m"]}])


@st.cache_data(ttl=600, show_spinner=False)
def get_hourly():
    r = requests.get(hurl, timeout=10); r.raise_for_status()
    h = r.json()["hourly"]
    return pd.DataFrame({"time": pd.to_datetime(h["time"]), "temperature": h["temperature_2m"]})


# --- Auto Refresh Controls ---
st.subheader("🔁 Auto Refresh Settings")
refresh_sec = st.slider("Refresh every (sec)", 10, 120, 30)
auto_refresh = st.toggle("Enable auto-refresh", value=False)
st.caption(f"Last refreshed at: {time.strftime('%H:%M:%S')}")

# --- Main view ---
try:
    df = get_weather()
except (requests.RequestException, KeyError) as e:
    st.warning(f"Weather API error: {e}\nShowing sample data so the demo continues.")
    df = SAMPLE_DF.copy()

# Keep a short history in session state (last 100 readings)
if "weather_history" not in st.session_state:
    st.session_state.weather_history = []

reading = df.iloc[0].to_dict()
reading["fetched_at"] = pd.Timestamp.now()
st.session_state.weather_history.append(reading)
st.session_state.weather_history = st.session_state.weather_history[-100:]
hist = pd.DataFrame(st.session_state.weather_history)

# Metrics: change vs. the previous reading
prev = hist.iloc[-2] if len(hist) > 1 else hist.iloc[-1]
c1, c2, c3 = st.columns(3)
c1.metric("Temperature", f"{reading['temperature']:.1f} °C",
          f"{reading['temperature'] - prev['temperature']:+.1f} °C")
c2.metric("Wind speed", f"{reading['wind']:.1f} km/h",
          f"{reading['wind'] - prev['wind']:+.1f} km/h")
c3.metric("Readings this session", len(hist))

st.subheader("Temperature over time (this session)")
fig = px.line(hist, x="fetched_at", y="temperature", markers=True,
              labels={"fetched_at": "Fetched at", "temperature": "Temperature (°C)"},
              title="Denver temperature — live readings")
st.plotly_chart(fig, use_container_width=True)
st.caption("Open-Meteo updates 'current' values every 15 minutes, and the cache lasts 10 minutes, "
           "so the line steps rather than changing on every refresh.")

st.subheader("Last 24 hours + today's forecast (hourly)")
try:
    hourly = get_hourly()
    fig_h = px.line(hourly, x="time", y="temperature",
                    labels={"time": "Time (Denver)", "temperature": "Temperature (°C)"},
                    title="Hourly temperature, Denver")
    fig_h.add_vline(x=pd.Timestamp.now(tz="America/Denver").tz_localize(None),
                    line_dash="dash", line_color="gray")
    st.plotly_chart(fig_h, use_container_width=True)
except (requests.RequestException, KeyError) as e:
    st.info(f"Hourly data unavailable: {e}")

with st.expander("Raw session history"):
    st.dataframe(hist, use_container_width=True)

# If auto-refresh is ON, wait and rerun the app
if auto_refresh:
    time.sleep(refresh_sec)
    get_weather.clear()
    st.rerun()
