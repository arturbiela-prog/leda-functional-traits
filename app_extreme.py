import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
import plotly.graph_objects as go
import base64
from sklearn.decomposition import PCA
from scipy.spatial.distance import cdist

# --- 1. FUNKCJA GENEROWANIA ESTETYCZNEGO RAPORTU ---
def generate_report_text(target, closest, farthest, fig_radar, fig_pcoa):
    def fig_to_base64(fig):
        try:
            img_bytes = fig.to_image(format="png", width=1000, height=600)
            return base64.b64encode(img_bytes).decode()
        except: return ""

    radar_img = fig_to_base64(fig_radar)
    pcoa_img = fig_to_base64(fig_pcoa)

    return f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
            body {{ font-family: 'Inter', sans-serif; margin: 50px; color: #1e293b; background-color: #ffffff; }}
            h1 {{ color: #064e3b; font-size: 28px; border-bottom: 3px solid #059669; padding-bottom: 10px; }}
            h2 {{ color: #065f46; font-size: 20px; margin-top: 40px; text-transform: uppercase; letter-spacing: 1px; }}
            .card {{ border: 1px solid #e2e8f0; border-radius: 12px; padding: 20px; margin: 20px 0; background: #f8fafc; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 15px; border-radius: 8px; overflow: hidden; }}
            th {{ background-color: #059669; color: white; padding: 12px; text-align: left; font-size: 14px; }}
            td {{ padding: 10px; border-bottom: 1px solid #e2e8f0; font-size: 14px; background: white; }}
            .img-container {{ text-align: center; margin-top: 20px; }}
            .img-container img {{ max-width: 100%; border-radius: 8px; border: 1px solid #e2e8f0; }}
            .footer {{ margin-top: 60px; font-size: 12px; color: #64748b; text-align: center; border-top: 1px solid #e2e8f0; padding-top: 20px; }}
        </style>
    </head>
    <body>
        <h1>Raport Ekologiczny: {target}</h1>
        <p>Analiza dystansu funkcjonalnego na podstawie bazy LEDA</p>

        <div class="card">
            <h2>1. Profil Funkcjonalny (Radar)</h2>
            <div class="img-container"><img src="data:image/png;base64,{radar_img}"></div>
        </div>

        <div class="card">
            <h2>2. Pozycja w przestrzeni cech (PCoA)</h2>
            <div class="img-container"><img src="data:image/png;base64,{pcoa_img}"></div>
        </div>

        <div class="card">
            <h2>3. Zestawienie Podobieństwa</h2>
            <h3>Gatunki najbardziej podobne</h3>
            {closest.to_html(index=False)}
            <br>
            <h3>Gatunki najbardziej odmienne</h3>
            {farthest.to_html(index=False)}
        </div>

        <div class="footer">
            Wygenerowano automatycznie | System Analizy LEDA | {pd.Timestamp.now().strftime('%Y-%m-%d')}
        </div>
    </body>
    </html>
    """

# --- 2. USTAWIENIA I DANE ---
st.set_page_config(page_title="Analiza LEDA", layout="wide")
st.title("Analiza Porównawcza Gatunków LEDA")

matrix_file = 'macierz_wynikowa.xlsx'
if not os.path.exists(matrix_file):
    st.error("Brak pliku macierz_wynikowa.xlsx")
else:
    df = pd.read_excel(matrix_file)
    name_col = df.columns[1]
    trait_cols = df.columns[2:]
    X = df[trait_cols].fillna(0)

    # --- 3. OBLICZENIA ---
    pca = PCA(n_components=2)
    coords = pca.fit_transform(X)
    df_pcoa = pd.DataFrame(coords, columns=['PC1', 'PC2'])
    df_pcoa['Gatunek'] = df[name_col]

    # --- 4. PASEK BOCZNY ---
    st.sidebar.header("Ustawienia Analizy")
    target_plant = st.sidebar.selectbox("Gatunek referencyjny:", df_pcoa['Gatunek'].unique())
    target_idx = df[df[name_col] == target_plant].index[0]
    
    # Dystanse
    target_vector = X.iloc[[target_idx]]
    distances = cdist(target_vector, X, metric='euclidean')[0]
    df_pcoa['Distance'] = distances
    df_sorted = df_pcoa[df_pcoa['Gatunek'] != target_plant].sort_values('Distance')
    
    najblizsze = df_sorted.head(5)
    najdalsze = df_sorted.tail(5)

    # --- 5. GÓRA: DWIE KOLUMNY (TABELE I RADAR) ---
    col_tabele, col_radar = st.columns([1, 2])
    
    with col_tabele:
        st.subheader("Gatunki podobne")
        st.table(najblizsze[['Gatunek', 'Distance']])
        
        st.subheader("Gatunki odmienne")
        st.table(najdalsze[['Gatunek', 'Distance']])

    with col_radar:
        st.subheader(f"Profil funkcjonalny: {target_plant}")
        base_traits = sorted(list(set([c.split('_v')[0] for c in trait_cols])))
        
        def get_radar_vals(idx):
            return [df.loc[idx, [c for c in trait_cols if c.startswith(bt)]].mean() for bt in base_traits]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=get_radar_vals(target_idx), theta=base_traits, fill='toself', name=target_plant))
        nn_idx = df[df[name_col] == najblizsze.iloc[0]['Gatunek']].index[0]
        fig_radar.add_trace(go.Scatterpolar(r=get_radar_vals(nn_idx), theta=base_traits, fill='toself', name="Najbliższy sąsiad"))
        
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), height=500, margin=dict(t=30, b=30))
        st.plotly_chart(fig_radar, use_container_width=True)

    st.divider()

    # --- 6. DÓŁ: PCoA (SZEROKI) ---
    st.subheader("Mapa PCoA (Principal Coordinate Analysis)")
    fig_pcoa = px.scatter(df_pcoa, x='PC1', y='PC2', text='Gatunek', color='Distance', color_continuous_scale='Viridis_r', height=700)
    fig_pcoa.update_traces(textposition='top center', marker=dict(size=15, line=dict(width=1, color='white')))
    st.plotly_chart(fig_pcoa, use_container_width=True)

    # --- 7. EKSPORT (W SIDEBARZE) ---
    report_content = generate_report_text(target_plant, 
                                         najblizsze[['Gatunek', 'Distance']], 
                                         najdalsze[['Gatunek', 'Distance']],
                                         fig_radar, fig_pcoa)
    
    st.sidebar.markdown("---")
    st.sidebar.download_button(
        label="📄 Pobierz Estetyczny Raport PDF",
        data=report_content,
        file_name=f"Raport_LEDA_{target_plant}.html",
        mime="text/html"
    )