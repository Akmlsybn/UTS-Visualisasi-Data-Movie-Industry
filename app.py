import streamlit as st
import pandas as pd
import altair as alt
import numpy as np

st.set_page_config(page_title="Dashboard Analisis Film", layout="wide")

st.markdown("""
<style>
    .main .block-container, [data-testid="stSidebar"] {
        background-color: #111111; /* Hitam pekat */
        color: #FFFFFF;
    }
    
    h1, h2, h3, .st-emotion-cache-16txtl3, .st-emotion-cache-qbe2hs, .st-emotion-cache-1gjd1a4, .st-emotion-cache-1cypcdb {
        color: #FFFFFF;
    }
    
    .st-emotion-cache-1629p8f, .st-emotion-cache-s49nzw, .st-emotion-cache-76cxyh, [data-testid="stSelectbox"] div[data-baseweb="select"] {
        background-color: #333333;
        border-color: #555555;
        color: #FFFFFF;
    }
    
    [data-testid="stAlert"] {
        color: #111111;
    }
    
    .st-emotion-cache-1g6gooi {
        color: #FFFFFF;
    }
</style>
""", unsafe_allow_html=True)
# cleaning data
@st.cache_data  
def load_and_clean_data(file_path):
    """
    Memuat data dan melakukan proses cleaning sesuai Poin 4 UAS.
    """
    try:
        df = pd.read_csv(file_path, sep=';')
    except Exception as e:
        st.error(f"Error membaca file: {e}. Pastikan file 'movies.csv' menggunakan pemisah ';'.")
        return pd.DataFrame() 

    # hapus kolom tidak relevan
    cols_to_drop = ['Unnamed: 15', 'Unnamed: 16', 'Unnamed: 17']
    cols_exist = [col for col in cols_to_drop if col in df.columns]
    df = df.drop(columns=cols_exist)

    # koreksi tipe data
    if 'score' in df.columns and df['score'].dtype == 'object':
        df['score'] = df['score'].str.replace(',', '.', regex=False)

    cols_to_numeric = ['budget', 'gross', 'score', 'votes', 'runtime', 'year']
    for col in cols_to_numeric:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # missing values handling
    key_columns = ['budget', 'gross', 'score', 'votes', 'year', 'genre', 'name', 'runtime']
    key_columns_exist = [col for col in key_columns if col in df.columns]
    
    rows_before = len(df)
    df = df.dropna(subset=key_columns_exist)
    rows_after = len(df)
    
    st.session_state.cleaning_info = f"Data dibersihkan: {rows_before - rows_after} baris data tidak valid/kosong telah dihapus."

    # data final
    df['year'] = df['year'].astype(int)
    df['votes'] = df['votes'].astype(int)
    df['runtime'] = df['runtime'].astype(int)

    # roi metrik (baru)
    if 'budget' in df.columns and 'gross' in df.columns:
        df = df[df['budget'] > 0] # Pastikan budget tidak nol
        df['roi'] = ((df['gross'] - df['budget']) / df['budget']) * 100

    return df

# load
df = load_and_clean_data('movies.csv')

if df.empty:
    st.error("Gagal memuat atau membersihkan data. Aplikasi berhenti.")
    st.stop()

# sidebar
st.sidebar.header('⚙️ Filter Dashboard')

year_list = sorted(df['year'].unique(), reverse=True)
year_list_asc = sorted(df['year'].unique()) 

selected_start_year = st.sidebar.selectbox(
    'Pilih Tahun Mulai:',
    options=year_list_asc, 
    index=0 
)

selected_end_year = st.sidebar.selectbox(
    'Pilih Tahun Akhir:',
    options=year_list, 
    index=0 
)

if selected_start_year > selected_end_year:
    st.sidebar.error("Tahun Mulai tidak boleh lebih besar dari Tahun Akhir.")
    selected_start_year = year_list_asc[0]
    selected_end_year = year_list[0]

all_genres = df['genre'].unique()

selected_genres = st.sidebar.multiselect(
    'Pilih Genre:',
    all_genres
)

df_filtered = df[
    (df['year'] >= selected_start_year) &
    (df['year'] <= selected_end_year)
]

if selected_genres: 
    df_filtered = df_filtered[
        df_filtered['genre'].isin(selected_genres)
    ]

if df_filtered.empty:
    st.warning("Tidak ada data yang cocok dengan filter Anda. Silakan ubah pilihan filter di sidebar.")
    st.stop()

# judul
st.title('🎬 Dashboard Analisis Faktor Kesuksesan Film')
st.caption(f"Menampilkan data untuk tahun {selected_start_year} - {selected_end_year} untuk genre yang dipilih.")


# ---------------------------------
# KPI CARDS (UPGRADE POIN 6 & OPSIONAL 5)
st.markdown("---")
st.subheader("Ringkasan Eksekutif (Sesuai Filter)")

# Fungsi untuk memformat angka besar
def format_large_number(num):
    if num >= 1_000_000_000:
        return f"${num / 1_000_000_000:.2f} Miliar"
    if num >= 1_000_000:
        return f"${num / 1_000_000:.2f} Juta"
    return f"${num / 1_000:.2f} Ribu"

# 1. Hitung metrik
total_gross = df_filtered['gross'].sum()
total_budget = df_filtered['budget'].sum()
avg_score = df_filtered['score'].mean()
avg_roi = df_filtered['roi'].mean() 

# 2. Buat kolom
col1, col2, col3, col4 = st.columns(4)

# 3. Tampilkan st.metric di setiap kolom
with col1:
    st.metric("Total Pendapatan (Gross)", f"{format_large_number(total_gross)} 💰")
with col2:
    st.metric("Total Anggaran (Budget)", f"{format_large_number(total_budget)} 💸")
with col3:
    st.metric("Rata-rata Score IMDb", f"{avg_score:.2f} ⭐")
with col4:
    st.metric("Rata-rata ROI", f"{avg_roi:.1f} % 📈") 

st.markdown("---")

# ---------------------------------
# VISUALISASI / DASHBOARD (POIN 5)
# ---------------------------------

# --- POIN 5 (Visualisasi 1: Line Chart) ---
st.header('Pertanyaan 1: Bagaimana tren budget dan gross film dari tahun ke tahun?')

df_trend = df_filtered.groupby('year')[['budget', 'gross']].mean().reset_index()
df_trend_melted = df_trend.melt('year', var_name='Tipe Metrik', value_name='Rata-rata Dolar (USD)')

chart1_colors = alt.Scale(domain=['gross', 'budget'], range=['gold', '#666666']) # Emas dan Abu-abu

chart1 = alt.Chart(df_trend_melted).mark_line(point=True).encode(
    x=alt.X('year:O', title='Tahun'), 
    y=alt.Y('Rata-rata Dolar (USD):Q', title='Rata-rata (USD)'),
    color=alt.Color('Tipe Metrik:N', scale=chart1_colors, title="Metrik Finansial"), 
    tooltip=['year', 'Tipe Metrik', alt.Tooltip('Rata-rata Dolar (USD):Q', format='$,.0f')]
)
st.altair_chart(chart1, use_container_width=True)

st.markdown("---")

# --- Tata Letak Kolom Baru (UPGRADE POIN 6) ---
col_a, col_b = st.columns(2)

with col_a:
    # --- POIN 5 (Visualisasi 2: Bar Chart) ---
    st.header('Pertanyaan 2: 5 Genre mana dengan rata-rata score tertinggi?')

    df_genre_score = df_filtered.groupby('genre')['score'].mean().nlargest(5).reset_index()

    chart2 = alt.Chart(df_genre_score).mark_bar(
        color='darkred' 
    ).encode(
        x=alt.X('score:Q', title='Rata-rata Score IMDb', scale=alt.Scale(domain=[0, 10])),
        y=alt.Y('genre:N', title='Genre', sort='-x'),
        tooltip=['genre', alt.Tooltip('score:Q', format='.2f')]
    ).properties(
        title='Top 5 Genre (dari Pilihan Filter) Berdasarkan Score Rata-rata'
    )
    st.altair_chart(chart2, use_container_width=True)

with col_b:
    # --- POIN 5 (Visualisasi 3: Scatter Plot) ---
    st.header('Pertanyaan 3: Apakah budget besar menjamin score tinggi?')

    chart3_colors = alt.Scale(scheme='inferno') 

    chart3 = alt.Chart(df_filtered).mark_circle(opacity=0.6, size=60).encode(
        x=alt.X('budget:Q', title='Budget (USD)', scale=alt.Scale(type="log")),
        y=alt.Y('score:Q', title='Score IMDb', scale=alt.Scale(domain=[0, 10])),
        tooltip=['name', 'genre', alt.Tooltip('budget:Q', format='$,.0f'), alt.Tooltip('score:Q', format='.1f')],
        color=alt.Color('genre:N', scale=chart3_colors, title="Genre")
    )
    st.altair_chart(chart3, use_container_width=True)


# --- PERUBAHAN: Upgrade "Top 10" dari Tabel menjadi Chart Visual ---
st.markdown("---")
st.header("🏆 Top 10 Film Terlaris (Sesuai Filter)")

# Ambil data Top 10 (angka mentah, jangan diformat)
top_10_gross_data = df_filtered.sort_values(by='gross', ascending=False).head(10)

# Buat Horizontal Bar Chart (seperti di screenshot Anda)
chart4 = alt.Chart(top_10_gross_data).mark_bar(color='gold').encode(
    x=alt.X('gross:Q', title='Pendapatan (Gross) - USD'),
    y=alt.Y('name:N', title='Nama Film', sort='-x'), # Sortir descending
    tooltip=[
        'name', 
        'year', 
        'genre', 
        alt.Tooltip('gross:Q', format='$,.0f'), # Format tooltip
        alt.Tooltip('budget:Q', format='$,.0f'),
        alt.Tooltip('roi:Q', format='.1f')
    ]
).properties(
    title='Top 10 Film Berdasarkan Pendapatan (Gross)'
)

st.altair_chart(chart4, use_container_width=True)
