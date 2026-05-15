import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import numpy as np

st.set_page_config(page_title="Daily HR Hitters", page_icon="⚾", layout="wide")

st.markdown("<h1 style='color:#FF6B35; font-size:2.6rem; font-weight:800;'>Daily HR Hitters</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#666; font-size:1.1rem;'>May 15, 2026 • Blended + Hot Form</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("Upload Data")
    matchups_file = st.file_uploader("Matchups CSV (required)", type="csv")
    hot_file = st.file_uploader("hot_hitters.csv", type="csv")
    
    st.divider()
    st.subheader("Hot Streak Settings")
    hot_boost = st.slider("Hot Player Boost", 0.0, 3.0, 1.5, 0.5)
    apply_hot = st.checkbox("Apply Hot Boost", value=True)

if matchups_file:
    df = pd.read_csv(matchups_file)
    df.columns = df.columns.str.strip()
    
    if 'Starter' in df.columns:
        df = df[df['Starter'] == 1]
    
    hr_col = [c for c in df.columns if 'HR Prob' in c][0]
    df['likelihood'] = pd.to_numeric(df[hr_col], errors='coerce').fillna(0)
    
    # Load hot hitters with encoding fix
    hot_set = set()
    if hot_file:
        try:
            hf = pd.read_csv(hot_file, encoding='utf-8-sig')
        except:
            hf = pd.read_csv(hot_file, encoding='latin1')
        
        hf.columns = hf.columns.str.strip()
        for _, row in hf.iterrows():
            name = str(row.get('Name', '')).lower().strip()
            if name:
                hot_set.add(name)
    
    def calculate_score(row):
        base = row['likelihood']
        name = str(row.get('Batter', '')).lower().strip()
        if apply_hot and name in hot_set:
            return base + hot_boost
        return base
    
    df['score'] = df.apply(calculate_score, axis=1)
    df['is_hot'] = df['Batter'].str.lower().str.strip().isin(hot_set)
    
    df = df.sort_values('score', ascending=False).reset_index(drop=True)
    df['rank'] = df.index + 1
    
    def get_why(row):
        reasons = []
        if row['is_hot']:
            reasons.append(f"Hot form (+{hot_boost})")
        return " | ".join(reasons) if reasons else "Good matchup"
    df['why'] = df.apply(get_why, axis=1)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Most Likely", "Hot Batters", "Best Value", "Top Picks"])
    
    with tab1:
        st.subheader("Most Likely HR Hitters Today")
        display = df[['rank', 'Batter', 'Team', 'Pitcher', 'score', 'why']].head(18)
        display.columns = ['Rank', 'Batter', 'Team', 'Pitcher', 'Likelihood %', 'Why']
        st.dataframe(display, use_container_width=True, hide_index=True,
                     column_config={"Likelihood %": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=12)})
    
    with tab2:
        st.subheader("Hot Batters (from hot_hitters.csv)")
        hot_df = df[df['is_hot']].sort_values('score', ascending=False)
        if len(hot_df) > 0:
            st.dataframe(hot_df[['Batter', 'Team', 'Pitcher', 'score']].head(15), use_container_width=True, hide_index=True)
        else:
            st.info("No players from your hot list have good matchups today.")
    
    with tab3:
        st.subheader("Best Value Plays")
        df['value'] = df['score'] * (df.get('proj_pa', 3.8) / 4)
        value_df = df.sort_values('value', ascending=False)
        st.dataframe(value_df[['Batter', 'Team', 'Pitcher', 'score', 'value']].head(12), use_container_width=True, hide_index=True)
    
    with tab4:
        st.subheader("Today's Top Recommendations")
        for i, row in df.head(6).iterrows():
            hot_tag = " 🔥 Hot" if row['is_hot'] else ""
            st.markdown(f"**#{row['rank']} {row['Batter']}**{hot_tag} ({row['Team']}) vs {row['Pitcher']}")
            st.caption(f"**{row['score']:.1f}%** — {row['why']}")

else:
    st.info("Upload Matchups CSV + hot_hitters.csv to begin.")