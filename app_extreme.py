import streamlit as st
import pandas as pd
import gower
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Analiza Ekstremów i Kontrybucji Cech", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_excel('macierz_wynikowa.xlsx')
    cols_d = [c for c in df.columns if '_d' in str(c)]
    # Zachowujemy oryginalne dane do analizy różnic (bez wypełniania średnią, by widzieć brak danych)
    numeric_df = df[cols_d]
    return df, numeric_df, cols_d

st.title("🌿 Detektyw Cech Funkcjonalnych")
st.markdown("Znajdź sobowtóry i sprawdź, które cechy decydują o ich podobieństwie lub odmienności.")

try:
    df, numeric_df, cols_d = load_data()
    # Wypełniamy kopię do obliczeń macierzy dystansu
    numeric_df_filled = numeric_df.fillna(numeric_df.mean())
    
    target_plant = st.selectbox("Wybierz gatunek odniesienia:", df['SBS name'].sort_values().unique())

    if target_plant:
        idx = df[df['SBS name'] == target_plant].index[0]
        distances = gower.gower_matrix(numeric_df_filled.iloc[[idx]], numeric_df_filled)[0]
        
        results = pd.DataFrame({'SBS name': df['SBS name'], 'Dystans': distances})
        similars = results[results['Dystans'] > 0].sort_values('Dystans').head(5)
        dissimilars = results.sort_values('Dystans', ascending=False).head(5)

        col1, col2 = st.columns([1, 1])
        with col1:
            st.success("✅ NAJBLIŻSZE")
            st.dataframe(similars.style.format({'Dystans': '{:.3f}'}))
        with col2:
            st.error("❌ NAJDALSZE")
            st.dataframe(dissimilars.style.format({'Dystans': '{:.3f}'}))

        st.divider()

        # SEKCJA: ANALIZA RÓŻNIC
        st.subheader("🔍 Dlaczego te rośliny się różnią?")
        compare_with = st.selectbox("Wybierz roślinę do szczegółowej analizy:", 
                                   options=pd.concat([similars, dissimilars])['SBS name'].tolist())
        
        comp_idx = df[df['SBS name'] == compare_with].index[0]

        # Obliczamy różnicę bezwzględną dla każdej cechy
        # Uwzględniamy normalizację zakresem (logika Gowera)
        diffs = []
        for col in cols_d:
            val_target = numeric_df_filled.iloc[idx][col]
            val_comp = numeric_df_filled.iloc[comp_idx][col]
            rng = numeric_df_filled[col].max() - numeric_df_filled[col].min()
            
            # Jeśli zakres jest 0, unikamy dzielenia przez zero
            diff = abs(val_target - val_comp) / rng if rng != 0 else 0
            diffs.append({'Cecha': col, 'Różnica (Skalowana)': diff, 'Wartość '+target_plant: val_target, 'Wartość '+compare_with: val_comp})

        diff_df = pd.DataFrame(diffs).sort_values('Różnica (Skalowana)', ascending=False)

        # Wyświetlamy 5 cech o największej różnicy
        c1, c2 = st.columns([2, 1])
        with c1:
            st.write(f"**Cechy generujące największy dystans między gatunkami:**")
            st.table(diff_df.head(5)[['Cecha', 'Wartość '+target_plant, 'Wartość '+compare_with]])
        
        with c2:
            # Radar dla tych 5 kluczowych cech różniących
            top_diff_features = diff_df.head(5)['Cecha'].tolist()
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(r=numeric_df_filled.iloc[idx][top_diff_features], theta=top_diff_features, fill='toself', name=target_plant))
            fig.add_trace(go.Scatterpolar(r=numeric_df_filled.iloc[comp_idx][top_diff_features], theta=top_diff_features, fill='toself', name=compare_with))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), title="Profil różnic")
            st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Błąd: {e}")