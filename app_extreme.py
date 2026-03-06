import streamlit as st
import pandas as pd
import gower
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Detektyw Cech Funkcjonalnych", layout="wide")

@st.cache_data
def load_data():
    df = pd.read_excel('macierz_wynikowa.xlsx')
    # WYMUSZENIE TEKSTU: Zamieniamy całą kolumnę nazw na tekst
    df['SBS name'] = df['SBS name'].astype(str)
    
    cols_to_exclude = ['SBS number', 'SBS name']
    all_feature_cols = [c for c in df.columns if c not in cols_to_exclude]
    
    numeric_df = df[all_feature_cols]
    return df, numeric_df, all_feature_cols

st.title("🌿 Detektyw Cech Funkcjonalnych")
st.markdown("Analiza podobieństwa na podstawie pełnej bazy cech LEDA (55+ wymiarów).")

try:
    df, numeric_df, all_feature_cols = load_data()
    numeric_df_filled = numeric_df.fillna(0)
    
    # Sortujemy nazwy i upewniamy się, że to lista tekstów
    species_list = sorted(df['SBS name'].unique().tolist())
    target_plant = st.selectbox("Wybierz gatunek odniesienia:", species_list)

    if target_plant:
        # Upewniamy się, że target_plant jest tekstem
        t_name = str(target_plant)
        idx = df[df['SBS name'] == t_name].index[0]
        
        distances = gower.gower_matrix(numeric_df_filled.iloc[[idx]], numeric_df_filled)[0]
        results = pd.DataFrame({'SBS name': df['SBS name'], 'Dystans': distances})
        
        similars = results[results['Dystans'] > 0].sort_values('Dystans').head(5)
        dissimilars = results.sort_values('Dystans', ascending=False).head(5)

        col1, col2 = st.columns([1, 1])
        with col1:
            st.success("✅ NAJBLIŻSZE (Sobowtóry funkcjonalne)")
            st.dataframe(similars.style.format({'Dystans': '{:.3f}'}))
        with col2:
            st.error("❌ NAJDALSZE (Przeciwieństwa)")
            st.dataframe(dissimilars.style.format({'Dystans': '{:.3f}'}))

        st.divider()

        st.subheader("🔍 Analiza kontrybucji cech")
        # Konwertujemy opcje wyboru na listę tekstów
        compare_options = list(map(str, pd.concat([similars, dissimilars])['SBS name'].tolist()))
        compare_with = st.selectbox("Wybierz roślinę do porównania:", options=compare_options)
        
        c_name = str(compare_with)
        comp_idx = df[df['SBS name'] == c_name].index[0]

        diffs = []
        for col in all_feature_cols:
            val_target = float(numeric_df_filled.iloc[idx][col])
            val_comp = float(numeric_df_filled.iloc[comp_idx][col])
            diff = abs(val_target - val_comp)
            
            diffs.append({
                'Cecha': col, 
                'Różnica': diff, 
                'Wartość '+ t_name: round(val_target, 3), 
                'Wartość '+ c_name: round(val_comp, 3)
            })

        diff_df = pd.DataFrame(diffs).sort_values('Różnica', ascending=False)

        c1, c2 = st.columns([1, 1])
        with c1:
            st.write(f"**Cechy generujące największe różnice:**")
            # Wyświetlamy tabelę z bezpiecznymi nazwami kolumn
            st.table(diff_df.head(10)[['Cecha', 'Wartość '+ t_name, 'Wartość '+ c_name]])
        
        with c2:
            top_features = diff_df.head(7)['Cecha'].tolist()
            
            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=numeric_df_filled.iloc[idx][top_features], 
                theta=top_features, 
                fill='toself', 
                name=t_name
            ))
            fig.add_trace(go.Scatterpolar(
                r=numeric_df_filled.iloc[comp_idx][top_features], 
                theta=top_features, 
                fill='toself', 
                name=c_name
            ))
            
            fig.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                title="Porównanie profilu cech (skala 0-1)"
            )
            st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Wystąpił błąd podczas analizy: {e}")