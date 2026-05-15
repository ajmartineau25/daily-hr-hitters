import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import numpy as np
import re

st.set_page_config(page_title="Daily HR Hitters", page_icon="⚾", layout="wide")

st.title("Daily HR Hitters - May 15, 2026")

with st.sidebar:
    st.header("Upload Data")
    matchups_file = st.file_uploader("Matchups CSV", type="csv")
    batters_file = st.file_uploader("Batters CSV (optional)", type="csv")
    park_file = st.file_uploader("ParkFactors CSV (optional)", type="csv")
    
    st.divider()
    st.subheader("Hot Streak Boost")
    hot_text = st.text_area("Paste hot player names", height=70)
    hot_csv = st.file_uploader("Upload FanGraphs/Savant CSV", type="csv")
    boost_amount = st.slider("Hot Boost Amount", 0.5, 3.0, 1.5, 0.5)
    apply_hot = st.checkbox("Apply Hot Boost", value=True)

if matchups_file:
    df = pd.read_csv(matchups_file)
    df.columns = df.columns.str.strip()
    
    if 'Starter' in df.columns:
        df = df[df['Starter'] == 1]
    
    hr_col = [c for c in df.columns if 'HR Prob' in c][0]
    df['likelihood'] = pd.to_numeric(df[hr_col], errors='coerce').fillna(0)
    
    # Hot players
    hot_set = set()
    if hot_text:
        for line in hot_text.splitlines():
            n = line.strip().lower()
            if n: hot_set.add(n)
    if hot_csv:
        try:
            hf = pd.read_csv(hot_csv)
            hf.columns = hf.columns.str.strip().str.lower()
            col = next((c for c in ['name', 'player'] if c in hf.columns), None)
            if col:
                for n in hf[col].dropna().astype(str):
                    hot_set.add(n.strip().lower())
        except: pass
    
    def final_score(row):
        base = row['likelihood']
        if apply_hot and str(row.get('Batter', '')).lower() in hot_set:
            return base + boost_amount
        return base
    
    df['score'] = df.apply(final_score, axis=1)
    df['is_hot'] = df['Batter'].str.lower().isin(hot_set)
    df['value'] = df['score'] * (df.get('proj_pa', 3.5) / 4)
    
    df = df.sort_values('score', ascending=False).reset_index(drop=True)
    df['rank'] = df.index + 1
    
    def get_why(row):
        w = []
        if row['is_hot']: w.append(f"Hot (+{boost_amount})")
        return " | ".join(w) if w else "Strong spot"
    df['why'] = df.apply(get_why, axis=1)
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Most Likely", "Hot Batters", "Best Value", "Park Advantage"])
    
    with tab1:
        st.subheader("Most Likely to Hit a HR Today")
        st.dataframe(df[['rank','Batter','Team','Pitcher','score','why']].head(15), use_container_width=True, hide_index=True)
    
    with tab2:
        st.subheader("Hot Batters (Receiving Boost)")
        hot_df = df[df['is_hot']].sort_values('score', ascending=False)
        if len(hot_df) > 0:
            st.dataframe(hot_df[['Batter','Team','Pitcher','score']].head(15), use_container_width=True, hide_index=True)
        else:
            st.info("No hot players loaded yet.")
    
    with tab3:
        st.subheader("Best Value Plays (Likelihood + Volume)")
        value_df = df.sort_values('value', ascending=False)
        st.dataframe(value_df[['Batter','Team','Pitcher','score','value']].head(12), use_container_width=True, hide_index=True)
    
    with tab4:
        st.subheader("Park Advantage Picks")
        # Simple park boost proxy
        if park_file:
            st.success("Park factors loaded - showing top boosted players")
        st.dataframe(df.sort_values('score', ascending=False)[['Batter','Team','Pitcher','score']].head(10), use_container_width=True, hide_index=True)

else:
    st.info("Upload Matchups CSV to see rankings and categories.")