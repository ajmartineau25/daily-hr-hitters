import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import numpy as np

st.set_page_config(page_title="Daily HR Hitters", page_icon="⚾", layout="wide")

st.markdown("<h1 style='color:#FF6B35; font-size:2.6rem; font-weight:800;'>Daily HR Hitters</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#666; font-size:1.1rem;'>May 15, 2026 • Ballpark Pal + Hot Form</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("Upload Data")
    matchups_file = st.file_uploader("Matchups CSV (required)", type="csv")
    hot_file = st.file_uploader("hot_hitters.csv (your Drive file)", type="csv")
    
    st.divider()
    st.subheader("Hot Streak Boost")
    hot_boost = st.slider("Boost for Hot Players", 0.0, 3.0, 1.5, 0.5)
    apply_hot = st.checkbox("Apply Hot Boost", value=True)

if matchups_file:
    df = pd.read_csv(matchups_file)
    df.columns = df.columns.str.strip()
    
    if 'Starter' in df.columns:
        df = df[df['Starter'] == 1]
    
    hr_col = [c for c in df.columns if 'HR Prob' in c][0]
    df['likelihood'] = pd.to_numeric(df[hr_col], errors='coerce').fillna(0)
    
    # Load hot_hitters.csv robustly
    hot_data = {}  # name -> dict of stats
    if hot_file:
        hf = None
        for enc in ['utf-8-sig', 'latin1', 'cp1252']:
            try:
                hf = pd.read_csv(hot_file, encoding=enc)
                if not hf.empty:
                    break
            except:
                continue
        
        if hf is not None and not hf.empty:
            hf.columns = hf.columns.str.strip()
            for _, row in hf.iterrows():
                name = str(row.get('Name', '')).lower().strip()
                if name:
                    hot_data[name] = {
                        'recent_hr': row.get('HR', 0),
                        'xwOBA': row.get('xwOBA', 0),
                        'Hard%': row.get('Hard%', 0)
                    }
        else:
            st.warning("Could not read hot_hitters.csv properly. Please re-export it as CSV from Google Sheets.")
    
    def get_score(row):
        base = row['likelihood']
        name = str(row.get('Batter', '')).lower().strip()
        if apply_hot and name in hot_data:
            return base + hot_boost
        return base
    
    df['score'] = df.apply(get_score, axis=1)
    df['is_hot'] = df['Batter'].str.lower().str.strip().isin(hot_data.keys())
    
    df = df.sort_values('score', ascending=False).reset_index(drop=True)
    df['rank'] = df.index + 1
    
    def get_why(row):
        reasons = []
        name = str(row.get('Batter', '')).lower().strip()
        if row['is_hot']:
            reasons.append(f"Hot recently (+{hot_boost})")
        return " | ".join(reasons) if reasons else "Solid matchup"
    df['why'] = df.apply(get_why, axis=1)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Most Likely", "Hot Batters", "Best Value", "Top Picks"])
    
    with tab1:
        st.subheader("Most Likely to Hit HRs Today")
        show = df[['rank','Batter','Team','Pitcher','score','why']].head(18)
        show.columns = ['Rank', 'Batter', 'Team', 'Pitcher', 'Likelihood %', 'Why']
        st.dataframe(show, use_container_width=True, hide_index=True,
                     column_config={"Likelihood %": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=12)})
    
    with tab2:
        st.subheader("Hot Batters (from your hot_hitters.csv)")
        hot_df = df[df['is_hot']].copy()
        if len(hot_df) > 0:
            # Merge some stats from hot_hitters.csv
            hot_df['Recent HRs'] = hot_df['Batter'].str.lower().map(lambda x: hot_data.get(x, {}).get('recent_hr', ''))
            hot_df['xwOBA'] = hot_df['Batter'].str.lower().map(lambda x: hot_data.get(x, {}).get('xwOBA', ''))
            hot_df['Hard%'] = hot_df['Batter'].str.lower().map(lambda x: hot_data.get(x, {}).get('Hard%', ''))
            
            st.dataframe(hot_df[['Batter', 'Team', 'Pitcher', 'score', 'Recent HRs', 'xwOBA', 'Hard%']].head(15), 
                        use_container_width=True, hide_index=True)
            st.caption("These players appear in your hot list and have good matchups today.")
        else:
            st.info("No players from your hot_hitters.csv have favorable matchups today.")
    
    with tab3:
        st.subheader("Best Value Plays (Likelihood + Volume)")
        df['value'] = df['score'] * (df.get('proj_pa', 3.8) / 4)
        st.dataframe(df.sort_values('value', ascending=False)[['Batter','Team','Pitcher','score','value']].head(12), use_container_width=True, hide_index=True)
    
    with tab4:
        st.subheader("Today's Top Recommendations")
        for i, row in df.head(6).iterrows():
            hot = " 🔥 Hot" if row['is_hot'] else ""
            st.markdown(f"**#{row['rank']} {row['Batter']}**{hot} ({row['Team']}) vs {row['Pitcher']}")
            st.caption(f"**{row['score']:.1f}% likelihood** — {row['why']}")

else:
    st.info("Upload your Matchups CSV and hot_hitters.csv to get started.")