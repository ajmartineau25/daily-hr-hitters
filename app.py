import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import numpy as np
import re

st.set_page_config(
    page_title="Daily HR Hitters",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.9rem;
        font-weight: 800;
        background: linear-gradient(90deg, #FF6B35, #F7931E);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 0.2rem;
    }
    .subheader { text-align: center; color: #555; font-size: 1.1rem; margin-bottom: 1.5rem; }
    .why-text { font-size: 0.9rem; color: #333; background: #fff7ed; padding: 8px 12px; border-radius: 8px; border-left: 4px solid #FF6B35; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">Daily HR Hitters</h1>', unsafe_allow_html=True)
st.markdown('<p class="subheader">May 15, 2026 • Blended + Hot Streak Aware</p>', unsafe_allow_html=True)

with st.sidebar:
    st.header("Upload Your Data")
    matchups_file = st.file_uploader("Matchups CSV (required)", type="csv")
    batters_file = st.file_uploader("Batters CSV", type="csv")
    park_file = st.file_uploader("ParkFactors CSV", type="csv")
    
    st.divider()
    st.subheader("Hot Streak / Form Boost")
    
    hot_text = st.text_area(
        "Paste hot player names (one per line or comma separated)",
        placeholder="Hunter Goodman\nCorbin Carroll\nNolan Arenado",
        height=100
    )
    
    hot_csv = st.file_uploader("Upload FanGraphs / Savant Hot CSV (optional)", type="csv")
    
    hot_boost = st.slider("Hot Streak Boost Amount", 0.0, 3.0, 1.5, 0.5)
    enable_hot = st.checkbox("Enable Hot Streak Boost", value=True)
    
    st.divider()
    st.subheader("Other Filters")
    min_score = st.slider("Min HR Likelihood %", 0.0, 12.0, 2.0, 0.5)
    show_starters_only = st.checkbox("Starting Lineup Only", value=True)

if matchups_file:
    matchups = pd.read_csv(matchups_file)
    matchups.columns = matchups.columns.str.strip()
    
    batters = pd.read_csv(batters_file) if batters_file else None
    if batters is not None:
        batters.columns = batters.columns.str.strip()
    
    parkfactors = pd.read_csv(park_file) if park_file else None
    
    if show_starters_only and 'Starter' in matchups.columns:
        df = matchups[matchups['Starter'] == 1].copy()
    else:
        df = matchups.copy()
    
    base_col = 'HR Prob' if 'HR Prob' in df.columns else 'HR Prob (no park)'
    df['base_hr'] = pd.to_numeric(df[base_col], errors='coerce').fillna(0)
    
    if batters is not None and 'HomeRunProbability' in batters.columns:
        b = batters[['FullName', 'HomeRunProbability', 'PlateAppearances']].copy()
        b.columns = ['Batter', 'proj_hr_prob', 'proj_pa']
        df = df.merge(b, on='Batter', how='left')
        df['proj_hr_prob'] = pd.to_numeric(df['proj_hr_prob'], errors='coerce').fillna(df['base_hr'])
        df['proj_pa'] = pd.to_numeric(df['proj_pa'], errors='coerce').fillna(3.5)
        df['composite'] = df['base_hr'] * 0.60 + df['proj_hr_prob'] * 0.40
    else:
        df['composite'] = df['base_hr']
        df['proj_pa'] = 3.5

    park_boost = 0.0
    if parkfactors is not None:
        try:
            if 'HR %' in parkfactors.columns:
                hr_pct = parkfactors['HR %'].astype(str).str.replace('%','').astype(float).mean() / 100
                park_boost = max(0, (hr_pct - 1.0) * 0.9)
        except:
            pass
    
    df['final_hr'] = df['composite'] * (1 + park_boost)
    
    # Hot Streak Logic
    hot_players = set()
    
    if hot_text:
        names = re.split(r'[,
]', hot_text)
        for name in names:
            clean = name.strip()
            if clean:
                hot_players.add(clean.lower())
    
    if hot_csv:
        try:
            hot_df = pd.read_csv(hot_csv)
            hot_df.columns = hot_df.columns.str.strip().str.lower()
            name_col = None
            for col in ['name', 'player', 'player name', 'batter']:
                if col in hot_df.columns:
                    name_col = col
                    break
            if name_col:
                for name in hot_df[name_col].dropna().astype(str):
                    hot_players.add(name.strip().lower())
        except:
            st.warning("Could not read the hot CSV")
    
    def apply_hot_boost(row):
        if enable_hot and row['Batter'].lower() in hot_players:
            return row['final_hr'] + hot_boost
        return row['final_hr']
    
    df['final_hr'] = df.apply(apply_hot_boost, axis=1)
    df['is_hot'] = df['Batter'].str.lower().isin(hot_players)
    
    df['value_score'] = (df['final_hr'] * (df['proj_pa'] / 4.0)).round(2)
    
    def smart_why(row):
        reasons = []
        if row.get('is_hot'):
            reasons.append(f"hot streak (+{hot_boost})")
        if float(row.get('HR Boost', 0)) > 8:
            reasons.append("strong sim boost vs pitcher")
        if park_boost > 0.04:
            reasons.append("park advantage")
        if row.get('proj_pa', 0) > 4.2:
            reasons.append("high volume")
        return " + ".join(reasons).capitalize() if reasons else "Solid projection"
    
    df['Why'] = df.apply(smart_why, axis=1)
    
    filtered = df[df['final_hr'] >= min_score].sort_values('final_hr', ascending=False)
    
    tab1, tab2, tab3 = st.tabs(["Rankings", "Value Plays", "Hot Streak"])
    
    with tab1:
        c1, c2, c3 = st.columns(3)
        c1.metric("Starters Analyzed", len(df))
        c2.metric("Qualified", len(filtered))
        c3.metric("Hot Players Boosted", len(hot_players))
        
        st.subheader("Rankings (Hot Streak Boosted)")
        
        cols = ['Batter', 'Team', 'Pitcher', 'final_hr', 'value_score', 'Why']
        if 'Game' in filtered.columns:
            cols.insert(2, 'Game')
        
        st.dataframe(filtered[cols].head(25), use_container_width=True, hide_index=True,
                     column_config={
                         "final_hr": st.column_config.ProgressColumn("HR Likelihood %", format="%.1f%%", min_value=0, max_value=15)
                     })
        
        st.subheader("Top Players")
        for i, (_, r) in enumerate(filtered.head(6).iterrows()):
            with st.container(border=True):
                tag = "Hot" if r['is_hot'] else ""
                st.markdown(f"**{r['Batter']}** {tag} — {r['final_hr']:.1f}%")
                st.caption(r['Why'])
    
    with tab2:
        st.subheader("Value Plays")
        value_plays = filtered.sort_values('value_score', ascending=False).head(12)
        if len(value_plays) > 0:
            st.dataframe(value_plays[['Batter','Team','final_hr','value_score','Why']].head(10), use_container_width=True, hide_index=True)
        else:
            st.info("No strong value plays at current thresholds.")
    
    with tab3:
        st.subheader("Hot Streak Management")
        if hot_players:
            st.success(f"Boosting {len(hot_players)} hot players (+{hot_boost})")
        else:
            st.info("No hot players loaded. Paste names or upload CSV above.")
    
    st.download_button("Download Rankings (CSV)", filtered.to_csv(index=False).encode(),
                       file_name=f"HR_Hitters_{datetime.now().strftime('%Y-%m-%d')}.csv")

else:
    st.info("Upload Matchups CSV to start.")

st.divider()
st.caption("v4 • Hot Streak + FanGraphs CSV Support")