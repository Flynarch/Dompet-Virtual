import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
from bs4 import BeautifulSoup
import datetime

# --- SETUP HALAMAN ---
st.set_page_config(page_title="Wealth Tracker Pro", page_icon="💎", layout="centered")

# --- KONEKSI KE GOOGLE SHEETS ---
# Kita pakai st.secrets biar aman (password gak ditaruh di codingan)
def connect_db():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Mengambil credentials dari Secret Streamlit Cloud
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    # Buka Spreadsheet berdasarkan nama file
    sheet = client.open("Database_Kekayaan")
    return sheet

# --- FUNGSI UPDATE HARGA LIVE ---
@st.cache_data(ttl=60)
def get_live_price(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        price_tag = soup.find('fin-streamer', {'data-field': 'regularMarketPrice'})
        if price_tag:
            price = float(price_tag.text.replace(',', ''))
            if "XAU" in ticker: price /= 31.1035 # Ounce ke Gram
            if "USD" in ticker: price *= 16200   # Kurs USD
            return price
    except:
        pass
    return 0

# --- LOAD DATA DARI SHEETS ---
try:
    sh = connect_db()
    ws_history = sh.worksheet("History")
    ws_portfolio = sh.worksheet("Portfolio")
except Exception as e:
    st.error("Gagal konek ke Google Sheets! Pastikan setup Secret benar.")
    st.stop()

# --- HITUNG SALDO MANUAL DARI HISTORY ---
# Kita ambil semua history, jumlahkan kolom Nominal
all_history = ws_history.get_all_records()
df_history = pd.DataFrame(all_history)

if not df_history.empty:
    # Pastikan kolom Nominal dianggap angka
    df_history['Nominal'] = pd.to_numeric(df_history['Nominal'])
    saldo_manual = df_history['Nominal'].sum()
else:
    saldo_manual = 0

# --- UI APLIKASI ---
st.title("💎 Wealth Tracker Pro")

# 1. INFO SALDO UTAMA
col1, col2 = st.columns(2)
col1.metric("💵 Uang Tunai (Manual)", f"Rp {saldo_manual:,.0f}")

# Hitung Investasi
portfolio_data = ws_portfolio.get_all_records()
total_investasi = 0
rincian_investasi = []

ASSET_CODES = {
    "Emas (Gram)": "XAU-IDR=X",
    "Bitcoin": "BTC-USD",
    "Saham BBCA": "BBCA.JK"
}

for item in portfolio_data:
    nama_aset = item['Aset']
    jumlah = float(item['Jumlah']) if item['Jumlah'] != '' else 0
    
    if jumlah > 0:
        harga = get_live_price(ASSET_CODES.get(nama_aset, ""))
        nilai = harga * jumlah
        total_investasi += nilai
        rincian_investasi.append({"Aset": nama_aset, "Jml": jumlah, "Nilai": nilai})

col2.metric("📈 Aset Investasi", f"Rp {total_investasi:,.0f}")
st.divider()
st.subheader(f"Total Kekayaan: Rp {saldo_manual + total_investasi:,.0f}")

# --- INPUT TRANSAKSI (FITUR BARU) ---
with st.container():
    st.write("### 📝 Catat Uang Masuk/Keluar")
    c1, c2, c3 = st.columns([2, 2, 1])
    ket = c1.text_input("Keterangan (ex: Gaji, Makan)")
    nom = c2.number_input("Nominal (Minus untuk pengeluaran)", step=10000)
    
    if c3.button("Simpan"):
        if ket and nom != 0:
            waktu = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            # Simpan ke Google Sheet tab History
            ws_history.append_row([waktu, ket, nom])
            st.success("Tersimpan!")
            st.rerun() # Refresh halaman
        else:
            st.warning("Isi keterangan & nominal!")

# --- LIHAT HISTORY (REQUEST KAMU) ---
# Ini fitur yang kamu minta "Pilih aja ada history gitu dipencet"
with st.expander("📜 Lihat Riwayat Transaksi Manual"):
    if not df_history.empty:
        # Tampilkan tabel, urutkan dari yang terbaru
        st.dataframe(df_history.sort_index(ascending=False), use_container_width=True)
    else:
        st.info("Belum ada data history.")

# --- UPDATE ASET ---
with st.expander("⚙️ Update Jumlah Aset Investasi"):
    aset_list = [d['Aset'] for d in portfolio_data]
    pilih_aset = st.selectbox("Pilih Aset", aset_list)
    jumlah_baru = st.number_input("Jumlah Total Terbaru", min_value=0.0, step=0.1)
    
    if st.button("Update Portfolio"):
        # Cari baris aset tersebut di Google Sheet
        cell = ws_portfolio.find(pilih_aset)
        ws_portfolio.update_cell(cell.row, 2, jumlah_baru) # Update kolom ke-2
        st.success("Portfolio Updated!")
        st.rerun()
