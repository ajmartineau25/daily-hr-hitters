import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import numpy as np
import unicodedata

def normalize_name(name):
    if pd.isna(name): return ""
    name = str(name).lower().strip()
    name = unicodedata.normalize('NFKD', name)
    name = ''.join([c for c in name if not unicodedata.combining(c)])
    return name

st.set_page_config(page_title="Daily HR Hitters", page_icon="⚾", layout="wide")

st.markdown("<h1 style='color:#FF6B35; font-size:2.6rem; font-weight:800;'>Daily HR Hitters</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#666; font-size:1.1rem;'>May 16, 2026 • Public Version (Google Sheets Backend)</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("Data Sources (Google Sheets)")
    
    st.markdown("""
    **How to use:**
    1. Put your Matchups and hot_hitters data in Google Sheets
    2. Make the sheets public (Anyone with the link can view)
    3. Paste the **export links** below
    """)
    
    matchups_url = st.text_input(
        "Matchups Sheet Export URL",
        value="https://docs.google.com/spreadsheets/d/YOUR_MATCHUPS_ID/export?format=csv&gid=0"
    )
    
    hot_url = st.text_input(
        "hot_hitters.csv Export URL",
        value="https://docs.google.com/spreadsheets/d/YOUR_HOT_ID/export?format=csv&gid=0"
    )
    
    st.divider()
    st.subheader("Hot Streak Settings")
    base_boost = st.slider("Base Hot Boost", 0.5, 2.0, 1.0, 0.25)
    apply_hot = st.checkbox("Apply Hot Boost", value=True)

# Load data from Google Sheets
@st.cache_data(ttl=300)  # Cache for 5 minutes

def load_data(url):
    try:
        return pd.read_csv(url)
    except Exception as e:
        st.error(f"Failed to load data from Google Sheets: {e}")
        return None

matchups_df = load_data(matchups_url) if matchups_url and "YOUR_" not in matchups_url else None
hot_df = load_data(hot_url) if hot_url and "YOUR_" not in hot_url else None

if matchups_df is not None:
    df = matchups_df.copy()
    df.columns = df.columns.str.strip()
    
    if 'Starter' in df.columns:
        df = df[df['Starter'] == 1]
    
    hr_col = [c for c in df.columns if 'HR Prob' in c][0]
    df['likelihood'] = pd.to_numeric(df[hr_col], errors='coerce').fillna(0)
    
    # Load hot data
    hot_data = {}
    if hot_df is not None and not hot_df.empty:
        hot_df.columns = hot_df.columns.str.strip()
        for _, row in hot_df.iterrows():
            name = normalize_name(row.get('Name', ''))
            if name:
                hard_str = str(row.get('Hard%', '0')).replace('%','')
                slg_str = str(row.get('SLG', '0')).replace('%','')
                hot_data[name] = {
                    'recent_hr': float(row.get('HR', 0) or 0),
                    'xwOBA': float(row.get('xwOBA', 0) or 0),
                    'HardPct': float(hard_str or 0),
                    'SLG': float(slg_str or 0)
                }
    
    def calculate_score(row):
        base = row['likelihood']
        name = normalize_name(row.get('Batter', ''))
        if apply_hot and name in hot_data:
            h = hot_data[name]
            form_boost = (h['recent_hr']*0.10 + h['xwOBA']*1.8 + h['HardPct']*0.05 + h['SLG']*4)
            return base + base_boost + form_boost
        return base
    
    df['score'] = df.apply(calculate_score, axis=1)
    df['is_hot'] = df.apply(lambda r: normalize_name(r.get('Batter','')) in hot_data, axis=1)
    
    df = df.sort_values('score', ascending=False).reset_index(drop=True)
    df['rank'] = df.index + 1
    
    def get_why(row):
        name = normalize_name(row.get('Batter', ''))
        if row['is_hot']:
            h = hot_data.get(name, {})
            return f"Hot (Hard%:{h.get('HardPct',0):.1f}, SLG:{h.get('SLG',0):.3f})"
        return "Good matchup"
    df['why'] = df.apply(get_why, axis=1)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Most Likely", "Hot Batters", "Best Value", "Top Picks"])
    
    with tab1:
        st.subheader("Most Likely HR Hitters Today")
        show = df[['rank','Batter','Team','Pitcher','score','why']].head(18)
        show.columns = ['Rank', 'Batter', 'Team', 'Pitcher', 'Likelihood %', 'Why']
        st.dataframe(show, use_container_width=True, hide_index=True,
                     column_config={"Likelihood %": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=15)})
    
    with tab2:
        st.subheader("Hot Batters (from your list)")
        hot_players = df[df['is_hot']].copy()
        if len(hot_players) > 0:
            hot_players['Recent HRs'] = hot_players['Batter'].apply(lambda x: hot_data.get(normalize_name(x), {}).get('recent_hr', ''))
            hot_players['Hard%'] = hot_players['Batter'].apply(lambda x: hot_data.get(normalize_name(x), {}).get('HardPct', ''))
            hot_players['SLG'] = hot_players['Batter'].apply(lambda x: hot_data.get(normalize_name(x), {}).get('SLG', ''))
            st.dataframe(hot_players[['Batter','Team','Pitcher','score','Recent HRs','Hard%','SLG']].head(15), use_container_width=True, hide_index=True)
        else:
            st.info("No hot players matched today's matchups.")
    
    with tab3:
        st.subheader("Best Value Plays")
        df['value'] = df['score'] * (df.get('proj_pa', 3.8) / 4)
        st.dataframe(df.sort_values('value', ascending=False)[['Batter','Team','Pitcher','score','value']].head(12), use_container_width=True, hide_index=True)
    
    with tab4:
        st.subheader("Top Recommendations")
        for i, row in df.head(6).iterrows():
            hot = " 🔥 Hot" if row['is_hot'] else ""
            st.markdown(f"**#{row['rank']} {row['Batter']}**{hot} ({row['Team']}) vs {row['Pitcher']}")
            st.caption(f"**{row['score']:.1f}%** — {row['why']}")

else:
    st.info("Please enter valid Google Sheets export URLs in the sidebar to load the data.")
    st.markdown("""
    **How to get the export URL:**
    1. Open your Google Sheet
    2. Click **Share** → Change to "Anyone with the link can view"
    3. Copy the sheet URL
    4. Replace `/edit#gid=0` with `/export?format=csv&gid=0`
    """)