import streamlit as st
import pandas as pd
import random
import requests
from datetime import datetime
import matplotlib.pyplot as plt
import seaborn as sns
import pydeck as pdk

# Page setup
st.set_page_config(page_title="🌍 Crisis Coordination Dashboard", layout="centered")
st.title("🤝 AI-Based Humanitarian Aid Coordination")

# Load district coordinates
coords_df = pd.read_csv("all_state_district_coordinates.csv")
coords_map = dict(zip(coords_df["District"], zip(coords_df["Latitude"], coords_df["Longitude"])))

# Government login
GOVT_USERNAME = "govt_user"
GOVT_PASSWORD = "secure123"
if "govt_logged_in" not in st.session_state:
    st.session_state.govt_logged_in = False

with st.sidebar:
    st.subheader("🔐 Government Login")
    if not st.session_state.govt_logged_in:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            st.session_state.govt_logged_in = True
            st.success(f"Logged in as: {username}")
    else:
        st.info("Logged in as government official.")

    st.markdown("## 🔍 Navigate")
    section = st.radio("Go to Section", [
        "Dashboard", "Map View", "Recommendations",
        "Resource Prioritization", "NGO Requests", "Approval Panel"
    ])

    st.markdown("## 🛠 Resource Capacity")
    total_food = st.number_input("Total Food Units", 0, 100000, 5000)
    total_medical = st.number_input("Total Medical Kits", 0, 10000, 1000)
    total_shelter = st.number_input("Total Shelter Units", 0, 10000, 500)

    st.markdown("## 🌟 Urgency Filter")
    urgency_level = st.selectbox(
        "Filter by Urgency",
        ["All", "🚨 Immediate Deployment", "⚠️ Urgent Support Required", "📊 Monitor Situation"]
    )

@st.cache_data
def get_districts_from_csv(state_name):
    df = pd.read_csv("full_indian_districts_updated.csv")
    return df[df["State"] == state_name]["District"].tolist()

@st.cache_data(ttl=1800)
def generate_district_data(state):
    districts = get_districts_from_csv(state)
    records = []
    for d in districts:
        lat, lon = coords_map.get(d, (None, None))
        severity = round(random.uniform(0.0, 1.0), 2)
        disruption = round(random.uniform(0.7, 1.0), 2)
        flood = min(10, int(disruption * 10))
        road = random.choices(["Blocked", "Low", "Medium", "High"], weights=[0.4, 0.2, 0.2, 0.2])[0]
        urgency = round(disruption * 0.4 + flood / 10 * 0.2 + severity * 0.2 + (0.2 if road == "Blocked" else 0), 2)
        recommendation = "🚨 Immediate Deployment" if urgency > 0.7 else "⚠️ Urgent Support Required" if urgency > 0.5 else "📊 Monitor Situation"
        records.append({
            "District": d,
            "Latitude": lat,
            "Longitude": lon,
            "Weather Severity": severity,
            "Disruption": disruption,
            "Flood": flood,
            "Road Access": road,
            "Urgency Score": urgency,
            "AI Recommendation": recommendation,
            "Population": random.randint(5000, 20000)
        })
    return pd.DataFrame(records)

selected_state = st.selectbox("Select a State", ["Telangana", "Maharashtra", "Delhi", "West Bengal", "Tamil Nadu", "Karnataka"])
if st.button("🔄 Refresh District Data"):
    st.session_state[selected_state] = generate_district_data(selected_state)
    st.session_state[f"{selected_state}_last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

if selected_state not in st.session_state:
    st.session_state[selected_state] = generate_district_data(selected_state)
    st.session_state[f"{selected_state}_last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

df_districts = st.session_state[selected_state]
last_updated = st.session_state.get(f"{selected_state}_last_updated", "Unknown")
st.markdown(f"🕒 **Last Updated**: `{last_updated}`")

if urgency_level != "All":
    df_districts = df_districts[df_districts["AI Recommendation"] == urgency_level]

if section == "Dashboard":
    st.subheader(f"📍 District-wise Data for {selected_state}")
    st.dataframe(df_districts)

    st.subheader("📉 Urgency Bar Chart")
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(df_districts["District"], df_districts["Urgency Score"], color='tomato')
    ax.set_title("Urgency Score by District")
    ax.set_xlabel("District")
    ax.set_ylabel("Urgency Score")
    ax.set_ylim(0, 1)
    ax.grid(axis='y')
    plt.xticks(rotation=90)
    st.pyplot(fig)

elif section == "Map View":
    st.subheader(f"🗺️ District Map of {selected_state}")
    df_districts["Color"] = df_districts["AI Recommendation"].apply(
        lambda x: [255, 0, 0, 180] if "Immediate" in x else [255, 165, 0, 160] if "Urgent" in x else [0, 128, 0, 120]
    )
    if not df_districts.empty and "Latitude" in df_districts.columns:
        map_layer = pdk.Layer(
            "ScatterplotLayer",
            data=df_districts.dropna(subset=["Latitude", "Longitude"]),
            get_position='[Longitude, Latitude]',
            get_color='Color',
            get_radius=20000,
            pickable=True
        )
        tooltip = {
            "html": "<b>{District}</b><br/>Urgency: {Urgency Score}<br/>Recommendation: {AI Recommendation}",
            "style": {"backgroundColor": "steelblue", "color": "white", "padding": "5px"}
        }
        view_state = pdk.ViewState(
            latitude=df_districts["Latitude"].mean(),
            longitude=df_districts["Longitude"].mean(),
            zoom=6,
            pitch=0
        )
        st.pydeck_chart(pdk.Deck(layers=[map_layer], initial_view_state=view_state, tooltip=tooltip))
    else:
        st.info("No coordinates available for districts in this state.")

elif section == "Recommendations":
    st.subheader("📊 AI Recommendations Summary")
    st.bar_chart(df_districts["AI Recommendation"].value_counts())
    st.line_chart(df_districts.sort_values(by="Urgency Score", ascending=False).set_index("District")["Urgency Score"])

elif section == "Resource Prioritization":
    st.subheader("📦 Resource Prioritization")
    df_districts["Food Needed"] = (df_districts["Urgency Score"] * df_districts["Population"] * 0.02).astype(int)
    df_districts["Shelter Needed"] = (df_districts["Urgency Score"] * df_districts["Population"] * 0.01).astype(int)
    df_districts["Medical Needed"] = (df_districts["Urgency Score"] * df_districts["Population"] * 0.015).astype(int)
    st.dataframe(df_districts[["District", "Urgency Score", "Population", "Food Needed", "Shelter Needed", "Medical Needed"]])

elif section == "NGO Requests":
    st.subheader("📨 NGO Aid Request")
    aid_region = st.selectbox("Select Region for Aid", df_districts["District"].unique())
    aid_type = st.text_input("Type of Aid (e.g. food, shelter, medical)")
    if "aid_requests" not in st.session_state:
        st.session_state.aid_requests = []
    if st.button("📤 Submit Aid Request") and aid_type:
        st.session_state.aid_requests.append({"Region": aid_region, "Aid Type": aid_type, "Status": "Pending"})
        st.success(f"Aid request submitted for {aid_region}!")

elif section == "Approval Panel":
    st.subheader("📬 Government Approval Panel")
    if st.session_state.govt_logged_in:
        requests_df = pd.DataFrame(st.session_state.aid_requests)
        if not requests_df.empty:
            for i, row in requests_df[requests_df["Status"] == "Pending"].iterrows():
                st.markdown(f"*Region: {row['Region']} | **Aid**: {row['Aid Type']}")
                if st.button(f"✅ Approve Request #{i}"):
                    st.session_state.aid_requests[i]["Status"] = "Approved"
                    st.success(f"Request for {row['Region']} approved.")
    else:
        st.warning("Login as government official to approve.")

st.subheader("🔥 Urgency Score Heatmap")
st.markdown(f"**Filtered Districts:** {len(df_districts)}")

if df_districts.empty:
    st.info("No districts match the selected urgency level. Try changing the filter to 'All'.")
elif len(df_districts) < 2:
    st.warning("Not enough data to generate a heatmap. At least two districts are needed.")
elif "Urgency Score" not in df_districts.columns:
    st.error("Urgency Score column missing in data.")
else:
    heat_df = df_districts[["District", "Urgency Score"]].copy()
    heat_df.set_index("District", inplace=True)
    fig, ax = plt.subplots(figsize=(10, len(heat_df) * 0.5))
    sns.heatmap(heat_df, annot=True, cmap="Reds", linewidths=0.5, fmt=".2f", ax=ax)
    st.pyplot(fig)
