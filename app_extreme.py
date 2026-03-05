import streamlit as st
import pandas as pd
import gower
import numpy as np
import plotly.graph_objects as go

# Konfiguracja strony
st.set_page_config(page_title="Analiza Ekstremów Funkcjonalnych", layout="wide")

@st.cache_data
def load_data():
    # Upewnij się, że ścieżka jest poprawna
    df = pd.read_excel(r'D:/LEDA/macierz_wynikowa.xlsx')
    # Automatyczne filtrowanie kolumn z wymiarami
    cols_d = [c for c in df.columns if '_d' in str(c)]
    numeric_df = df[cols_d].fillna(df[cols_d].mean())
    return df, numeric_df, cols_d

st.title("🏹 Analiza Podobieństwa i Kontrastu Funkcjonalnego")
st.markdown("Ten moduł pozwala znaleźć rośliny najbardziej podobne (sobowtóry) oraz najbardziej odmienne (anty-sobowtóry).")

try:
    df, numeric_df, cols_d = load_data()
    
    # Lista gatunków do wyboru
    target_plant = st.selectbox("Wybierz gatunek odniesienia:", df['SBS name'].sort_values().unique())

    if target_plant:
        idx = df[df['SBS name'] == target_plant].index[0]
        
        # Obliczanie dystansu Gowera dla wybranej rośliny
        distances = gower.gower_matrix(numeric_df.iloc[[idx]], numeric_df)[0]
        
        results = pd.DataFrame({
            'SBS name': df['SBS name'],
            'SBS number': df['SBS number'],
            'Dystans': distances
        })

        # Przygotowanie list
        similars = results[results['Dystans'] > 0].sort_values('Dystans').head(5)
        dissimilars = results.sort_values('Dystans', ascending=False).head(5)

        # Układ kolumn
        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            st.success("✅ NAJBLIŻSZE (Top 5)")
            st.dataframe(similars[['SBS name', 'Dystans']].style.format({'Dystans': '{:.3f}'}))

        with col2:
            st.error("❌ NAJDALSZE (Top 5)")
            st.dataframe(dissimilars[['SBS name', 'Dystans']].style.format({'Dystans': '{:.3f}'}))

        with col3:
            st.subheader("Porównanie profili na wykresie radarowym")
            
            # Połączone opcje do wyboru na wykresie
            compare_with = st.selectbox(
                "Wybierz gatunek do nałożenia na radar:",
                options=pd.concat([similars, dissimilars])['SBS name'].tolist()
            )
            
            comp_idx = df[df['SBS name'] == compare_with].index[0]

            # Wybór cech do radaru (wybieramy pierwsze 15 wymiarów dla czytelności)
            radar_features = cols_d[:15] 

            fig = go.Figure()
            # Gatunek bazowy
            fig.add_trace(go.Scatterpolar(
                r=numeric_df.iloc[idx][radar_features].values,
                theta=radar_features,
                fill='toself',
                name=target_plant,
                line_color='blue'
            ))
            # Gatunek porównawczy
            fig.add_trace(go.Scatterpolar(
                r=numeric_df.iloc[comp_idx][radar_features].values,
                theta=radar_features,
                fill='toself',
                name=compare_with,
                line_color='red'
            ))

            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                showlegend=True,
                height=500
            )
            st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Coś poszło nie tak: {e}")