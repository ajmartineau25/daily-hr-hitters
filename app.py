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
st.markdown("<p style='color:#666; font-size:1.1rem;'>May 15, 2026 • Diagnostics Mode</p>", unsafe_allow_html=True)

with st.sidebar:
    st.header("Upload Data")
    matchups_file = st.file_uploader("Matchups CSV (required)", type="csv")
    hot_file = st.file_uploader("hot_hitters.csv", type="csv")
    
    st.divider()
    st.subheader("Hot Streak Settings")
    base_boost = st.slider("Base Hot Boost", 0.5, 2.0, 1.0, 0.25)
    apply_hot = st.checkbox("Apply Hot Boost", value=True)

if matchups_file:
    df = pd.read_csv(matchups_file)
    df.columns = df.columns.str.strip()
    
    if 'Starter' in df.columns:
        df = df[df['Starter'] == 1]
    
    hr_col = [c for c in df.columns if 'HR Prob' in c][0]
    df['likelihood'] = pd.to_numeric(df[hr_col], errors='coerce').fillna(0)
    
    # === Hot file diagnostics ===
    hot_data = {}
    hot_loaded_count = 0
    hot_sample_names = []
    
    if hot_file:
        hf = None
        for enc in ['utf-8-sig', 'latin1', 'cp1252']:
            try:
                hf = pd.read_csv(hot_file, encoding=enc)
                if not hf.empty: break
            except: continue
        
        if hf is not None and not hf.empty:
            hf.columns = hf.columns.str.strip()
            for _, row in hf.iterrows():
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
            hot_loaded_count = len(hot_data)
            hot_sample_names = list(hot_data.keys())[:5]
        else:
            st.error("Failed to read hot_hitters.csv even after trying multiple encodings.")
    
    # Show diagnostics in sidebar
    if hot_loaded_count > 0:
        st.sidebar.success(f"Loaded {hot_loaded_count} hot players from your file")
        st.sidebar.caption(f"Sample names: {', '.join(hot_sample_names)}")
    elif hot_file:
        st.sidebar.warning("hot_hitters.csv was uploaded but no players were loaded.")
    
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
        st.subheader("Hot Batters")
        hot_df = df[df['is_hot']].copy()
        matched_count = len(hot_df)
        
        if matched_count > 0:
            hot_df['Recent HRs'] = hot_df['Batter'].apply(lambda x: hot_data.get(normalize_name(x), {}).get('recent_hr', ''))
            hot_df['Hard%'] = hot_df['Batter'].apply(lambda x: hot_data.get(normalize_name(x), {}).get('HardPct', ''))
            hot_df['SLG'] = hot_df['Batter'].apply(lambda x: hot_data.get(normalize_name(x), {}).get('SLG', ''))
            st.dataframe(hot_df[['Batter','Team','Pitcher','score','Recent HRs','Hard%','SLG']].head(15), use_container_width=True, hide_index=True)
        else:
            st.warning(f"No hot players matched today's matchups.")
            st.info(f"Loaded {hot_loaded_count} players from hot_hitters.csv, but 0 matched the current Matchups file.")
            if hot_loaded_count > 0:
                st.caption("This usually means name differences between the two files (even small ones).")
    
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
    st.info("Upload Matchups CSV + hot_hitters.csv to begin.")