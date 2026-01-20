import streamlit as st
import requests
from bs4 import BeautifulSoup
import json
import os
import pandas as pd

# --- KONFIGURASI ---
st.set_page_config(page_title="My Wealth Tracker", page_icon="💰", layout="centered")
DB_FILE = "dompet_saya.json"

# --- FUNGSI BACKEND (SAMA SEPERTI SEBELUMNYA) ---
def load_data():
    if not os.path.exists(DB_FILE):
        return {"cash": 0, "investments": {"Emas (Gram)": 0, "Bitcoin": 0, "Saham BBCA": 0}}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_data(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_live_price(ticker):
    # Menggunakan cache agar tidak nembak server Yahoo terus menerus setiap klik
    return fetch_price(ticker)

@st.cache_data(ttl=60) # Data disimpan 60 detik di memori
def fetch_price(ticker):
    url = f"https://finance.yahoo.com/quote/{ticker}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        price_tag = soup.find('fin-streamer', {'data-field': 'regularMarketPrice'})
        if price_tag:
            price = float(price_tag.text.replace(',', ''))
            if "XAU" in ticker: price /= 31.1035 # Ounce to Gram
            if "USD" in ticker: price *= 16200   # Estimasi Kurs
            return price
    except:
        pass
    return 0

# --- TAMPILAN APLIKASI (FRONTEND) ---
st.title("💰 Wealth Dashboard")
st.markdown("Pantau kekayaanmu *real-time* dari mana saja.")

# Load Data
data = load_data()

# --- SIDEBAR (INPUT DATA) ---
st.sidebar.header("⚙️ Update Aset")

# Update Uang Tunai
st.sidebar.subheader("Dompet Manual")
cash_input = st.sidebar.number_input("Saldo Uang Tunai (Rp)", value=float(data['cash']), step=100000.0)
if st.sidebar.button("Simpan Saldo"):
    data['cash'] = cash_input
    save_data(data)
    st.sidebar.success("Saldo Disimpan!")
    st.rerun()

# Update Investasi
st.sidebar.subheader("Portofolio Investasi")
asset_choice = st.sidebar.selectbox("Pilih Aset", list(data['investments'].keys()))
qty_input = st.sidebar.number_input(f"Jumlah {asset_choice}", value=float(data['investments'][asset_choice]))

if st.sidebar.button("Update Aset"):
    data['investments'][asset_choice] = qty_input
    save_data(data)
    st.sidebar.success("Aset Disimpan!")
    st.rerun()

# --- HALAMAN UTAMA (VISUALISASI) ---

# 1. Kalkulasi Total
ASSET_MAPPING = {
    "Emas (Gram)": "XAU-IDR=X",  
    "Bitcoin": "BTC-USD",
    "Saham BBCA": "BBCA.JK"
}

total_investasi = 0
rincian_aset = []

for asset, qty in data['investments'].items():
    if qty > 0:
        price = get_live_price(ASSET_MAPPING[asset])
        val = price * qty
        total_investasi += val
        rincian_aset.append({"Aset": asset, "Jumlah": qty, "Harga Pasar": price, "Total Nilai": val})

grand_total = data['cash'] + total_investasi

# 2. Tampilkan Big Numbers (Metrics)
col1, col2 = st.columns(2)
col1.metric("💵 Uang Tunai", f"Rp {data['cash']:,.0f}")
col2.metric("📈 Nilai Investasi", f"Rp {total_investasi:,.0f}")

st.divider()
st.metric("💎 TOTAL KEKAYAAN BERSIH", f"Rp {grand_total:,.0f}", delta_color="normal")

# 3. Tabel Detail
if rincian_aset:
    st.subheader("Rincian Aset")
    df = pd.DataFrame(rincian_aset)
    # Format Rupiah di Tabel
    st.dataframe(df.style.format({"Harga Pasar": "Rp {:,.0f}", "Total Nilai": "Rp {:,.0f}"}))

    # 4. Bonus: Grafik Lingkaran
    st.subheader("Komposisi Kekayaan")
    chart_data = {"Aset": ["Uang Tunai"] + [x['Aset'] for x in rincian_aset], 
                  "Nilai": [data['cash']] + [x['Total Nilai'] for x in rincian_aset]}
    st.bar_chart(pd.DataFrame(chart_data).set_index("Aset"))

else:
    st.info("Belum ada aset investasi. Tambahkan di menu sebelah kiri/atas (tanda panah).")
