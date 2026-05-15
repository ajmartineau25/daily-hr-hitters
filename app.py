import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import numpy as np

st.set_page_config(page_title="Daily HR Hitters", page_icon="⚾", layout="wide")

st.title("Daily HR Hitters - May 15, 2026")

with st.sidebar:
    st.header("Upload Data")
    matchups_file = st.file_uploader("Matchups CSV", type="csv")
    batters_file = st.file_uploader("Batters CSV (optional)", type="csv")
    park_file = st.file_uploader("ParkFactors CSV (optional)", type="csv")
    
    st.divider()
    st.subheader("Hot Streak Boost")
    hot_names_text = st.text_area("Paste hot player names (one per line)", height=80)
    hot_csv = st.file_uploader("Upload FanGraphs/Savant CSV (optional)", type="csv")
    hot_boost = st.slider("Boost Amount", 0.0, 3.0, 1.5, 0.5)
    use_hot = st.checkbox("Apply Hot Streak Boost", value=True)

if matchups_file:
    df = pd.read_csv(matchups_file)
    df.columns = df.columns.str.strip()
    
    if 'Starter' in df.columns:
        df = df[df['Starter'] == 1]
    
    # Get HR Prob column
    hr_col = 'HR Prob' if 'HR Prob' in df.columns else df.filter(like='HR Prob').columns[0]
    df['likelihood'] = pd.to_numeric(df[hr_col], errors='coerce').fillna(0)
    
    # Hot players set
    hot_set = set()
    
    if hot_names_text:
        for line in hot_names_text.splitlines():
            name = line.strip().lower()
            if name:
                hot_set.add(name)
    
    if hot_csv:
        try:
            hdf = pd.read_csv(hot_csv)
            hdf.columns = hdf.columns.str.strip().str.lower()
            namecol = None
            for c in ['name', 'player', 'player name']:
                if c in hdf.columns:
                    namecol = c
                    break
            if namecol:
                for n in hdf[namecol].dropna().astype(str):
                    hot_set.add(n.strip().lower())
        except:
            pass
    
    if use_hot and hot_set:
        def boost_row(row):
            if str(row.get('Batter', '')).lower() in hot_set:
                return row['likelihood'] + hot_boost
            return row['likelihood']
        df['likelihood'] = df.apply(boost_row, axis=1)
    
    df = df.sort_values('likelihood', ascending=False)
    
    st.subheader("Rankings")
    st.dataframe(df[['Batter', 'Team', 'Pitcher', 'likelihood']].head(25), use_container_width=True)
    
    if hot_set:
        st.success(f"Applied hot streak boost to {len(hot_set)} players")
else:
    st.info("Upload Matchups CSV to begin")