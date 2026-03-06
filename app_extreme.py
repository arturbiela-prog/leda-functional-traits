import streamlit as st
import pandas as pd
import numpy as np
import os
import plotly.express as px
import plotly.graph_objects as go
from sklearn.decomposition import PCA
from scipy.spatial.distance import cdist

# --- 1. FUNKCJA ŁADOWANIA WAG ---
def load_weights(file_path):
    if os.path.exists(file_path):
        try:
            w_df = pd.read_csv(file_path, sep=None, engine='python')
            w_df.columns = [c.strip() for c in w_df.columns]
            # Szukamy kolumn niezależnie od wielkości liter
            t_col = [c for c in w_df.columns if c.lower() == 'trait'][0]
            w_col = [c for c in w_df.columns if c.lower() == 'weight'][0]
            return dict(zip(w_df[t_col], w_df[w_col]))
        except: return {}
    return {}

# --- 2. KONFIGURACJA STRONY ---
st.set_page_config(page_title="Doktorat LEDA - PCoA", layout="wide")
st.title("Analiza Porównawcza Gatunków LEDA")

matrix_file = 'macierz_wynikowa.xlsx'
weights_file = 'wagi.csv'

if not os.path.exists(matrix_file):
    st.error(f"Nie znaleziono pliku {matrix_file}. Upewnij się, że analiza.py zadziałała.")
else:
    # --- 3. WCZYTYWANIE DANYCH ---
    df = pd.read_excel(matrix_file)
    weights = load_weights(weights_file)
    
    # Rozpoznanie kolumn na podstawie Twojego pliku
    # Kolumna 0: SBS number, Kolumna 1: SBS name, Reszta: Cechy
    name_col = df.columns[1] 
    trait_cols = df.columns[2:]
    
    # Przygotowanie danych (X) do obliczeń
    X = df[trait_cols].fillna(0)
    for col in X.columns:
        base_trait = col.split('_v')[0]
        X[col] = X[col] * weights.get(base_trait, 1.0)

    # --- 4. OBLICZENIA PCoA ---
    pca = PCA(n_components=2)
    coords = pca.fit_transform(X)
    df_pcoa = pd.DataFrame(coords, columns=['PC1', 'PC2'])
    df_pcoa['Gatunek'] = df[name_col]

    # --- 5. WYBÓR ROŚLINY I SĄSIEDZTWO ---
    st.sidebar.header("Wybierz roślinę do analizy")
    target_plant = st.sidebar.selectbox("Gatunek referencyjny:", df_pcoa['Gatunek'].unique())

    # Obliczanie dystansów euklidesowych w przestrzeni cech (Gower-like)
    # Wybieramy wektor cech wybranej rośliny
    target_idx = df[df[name_col] == target_plant].index[0]
    target_vector = X.iloc[[target_idx]]
    
    # Dystans do wszystkich innych
    distances = cdist(target_vector, X, metric='euclidean')[0]
    df_pcoa['Distance'] = distances
    
    # Sortowanie
    df_sorted = df_pcoa[df_pcoa['Gatunek'] != target_plant].sort_values('Distance')
    najblizsze = df_sorted.head(5)
    najdalsze = df_sorted.tail(5)

    # --- 6. WIZUALIZACJA: WYKRES PCoA ---
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Przestrzeń cech (PCoA)")
        fig_pcoa = px.scatter(df_pcoa, x='PC1', y='PC2', text='Gatunek', 
                             color='Distance', color_continuous_scale='Viridis',
                             height=700)
        fig_pcoa.update_traces(textposition='top center', marker=dict(size=12))
        st.plotly_chart(fig_pcoa, use_container_width=True)

    with col2:
        st.subheader("Sąsiedztwo ekologiczne")
        st.write("**5 Najbardziej podobnych:**")
        st.dataframe(najblizsze[['Gatunek', 'Distance']], hide_index=True)
        
        st.write("**5 Najbardziej odmiennych:**")
        st.dataframe(najdalsze[['Gatunek', 'Distance']], hide_index=True)

    st.divider()

    # --- 7. WYKRES RADAROWY ---
    st.subheader(f"Profil cech: {target_plant}")
    
    # Przygotowanie danych do radaru (tylko główne cechy, bez wektorów _v)
    # Agregujemy kolumny wektorowe do średniej, żeby radar był czytelny
    main_traits = sorted(list(set([c.split('_v')[0] for c in trait_cols])))
    
    radar_vals = []
    for mt in main_traits:
        related_cols = [c for c in trait_cols if c.startswith(mt)]
        val = df.loc[target_idx, related_cols].mean()
        radar_vals.append(val)

    fig_radar = go.Figure()
    fig_radar.add_trace(go.Scatterpolar(
        r=radar_vals,
        theta=main_traits,
        fill='toself',
        name=target_plant,
        line_color='green'
    ))
    
    # Dodanie najbliższego sąsiada dla porównania
    nearest_neighbor_name = najblizsze.iloc[0]['Gatunek']
    nn_idx = df[df[name_col] == nearest_neighbor_name].index[0]
    nn_vals = []
    for mt in main_traits:
        related_cols = [c for c in trait_cols if c.startswith(mt)]
        nn_vals.append(df.loc[nn_idx, related_cols].mean())

    fig_radar.add_trace(go.Scatterpolar(
        r=nn_vals,
        theta=main_traits,
        fill='toself',
        name=f"Najbliższy: {nearest_neighbor_name}",
        line_color='rgba(255, 0, 0, 0.5)'
    ))

    fig_radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        height=600
    )
    st.plotly_chart(fig_radar, use_container_width=True)