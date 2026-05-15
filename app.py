import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import numpy as np
import re

st.set_page_config(page_title="Daily HR Hitters", page_icon="⚾", layout="wide")

st.markdown("""
<style>
    .main-header { font-size: 2.6rem; font-weight: 800; color: #FF6B35; }
    .hot-badge { background-color: #fee2e2; color: #9f1239; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">Daily HR Hitters - May 15, 2026</h1>', unsafe_allow_html=True)

with st.sidebar:
    st.header("Upload Data")
    matchups = st.file_uploader("Matchups CSV", type="csv")
    batters = st.file_uploader("Batters CSV (optional)", type="csv")
    park = st.file_uploader("ParkFactors CSV (optional)", type="csv")
    
    st.divider()
    st.subheader("Hot Streak Boost")
    hot_text = st.text_area("Paste hot players (one per line)", height=80)
    hot_file = st.file_uploader("Upload FanGraphs/Savant CSV", type="csv")
    boost = st.slider("Boost Amount", 0.5, 3.0, 1.5, 0.5)
    use_boost = st.checkbox("Enable Hot Boost", value=True)

if matchups:
    df = pd.read_csv(matchups)
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
    if hot_file:
        try:
            hf = pd.read_csv(hot_file)
            hf.columns = hf.columns.str.strip().str.lower()
            col = next((c for c in ['name','player','player name'] if c in hf.columns), None)
            if col:
                for n in hf[col].dropna().astype(str).str.lower():
                    hot_set.add(n.strip())
        except: pass
    
    def get_final(row):
        base = row['likelihood']
        if use_boost and str(row.get('Batter','')).lower() in hot_set:
            return base + boost
        return base
    
    df['final'] = df.apply(get_final, axis=1)
    df['is_hot'] = df['Batter'].str.lower().isin(hot_set)
    
    df = df.sort_values('final', ascending=False).reset_index(drop=True)
    df['rank'] = df.index + 1
    
    # Why
    def why_text(row):
        reasons = []
        if row['is_hot']: reasons.append(f"Hot streak (+{boost})")
        return " | ".join(reasons) if reasons else "Strong projection"
    df['why'] = df.apply(why_text, axis=1)
    
    # Metrics
    c1, c2, c3 = st.columns(3)
    c1.metric("Players Analyzed", len(df))
    c2.metric("Hot Players Boosted", len(hot_set))
    c3.metric("Top Likelihood", f"{df['final'].max():.1f}%")
    
    st.subheader("Today's Rankings")
    
    display = df[['rank', 'Batter', 'Team', 'Pitcher', 'final', 'why']].head(20)
    display.columns = ['Rank', 'Batter', 'Team', 'Pitcher', 'Likelihood %', 'Why']
    
    st.dataframe(display, use_container_width=True, hide_index=True,
                 column_config={
                     "Likelihood %": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=12)
                 })
    
    st.subheader("Top Recommendations")
    for i, row in df.head(5).iterrows():
        hot = " 🔥 Hot" if row['is_hot'] else ""
        st.markdown(f"**#{row['rank']} {row['Batter']}**{hot} ({row['Team']}) vs {row['Pitcher']} — **{row['final']:.1f}%**")
        st.caption(row['why'])
else:
    st.info("Upload your Matchups CSV to see rankings.")