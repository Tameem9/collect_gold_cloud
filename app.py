import html
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="Egypt Gold & USD Tracker", page_icon="💛", layout="wide")

st.markdown("""
<style>
.stApp {background: radial-gradient(circle at 5% 0%, #fff1cb 0%, transparent 34%), radial-gradient(circle at 95% 12%, #e0f6ed 0%, transparent 32%), #faf9f6; color:#24312c;}
.block-container {max-width: 1350px; padding-top: 1.5rem;}
h1,h2,h3 {color:#263b31!important;}
.hero {text-align:center; margin: 1.0rem 0 1.7rem;}
.hero h1 {font-size:clamp(1.7rem,3vw,2.9rem); margin:0; color:#263b31;}
.hero p {color:#69756d; margin:.45rem 0 0;}
.price-card {border:1px solid #e7ddc5; background:linear-gradient(155deg,#ffffff,#fff9e9); border-radius:19px; padding:20px 8px; text-align:center; min-height:160px; box-shadow:0 8px 24px rgba(70,57,29,.06); display:flex; flex-direction:column; justify-content:center; align-items:center;}
.price-card.fx {background:linear-gradient(155deg,#e8f8f0,#f8fff9);border-color:#cde9db;}
.price {font-size:clamp(1.05rem,1.7vw,1.7rem);font-weight:800;color:#263b31;white-space:nowrap;}
.price-label {font-size:.95rem;color:#6e776e;font-weight:650;margin-top:8px;}
.movement {font-size:.85rem;font-weight:700;margin-top:7px;}
.up {color:#128448;} .down {color:#c43e42;} .flat {color:#788079;}
.update-pill {float:right; border:1px solid #d7e6db;background:#f1fbf4;border-radius:12px;padding:9px 13px;font-size:.78rem;color:#52665b;}
@media (max-width:650px) {.price-card {min-height:130px;padding:13px 5px}.price {font-size:1.05rem}.price-label {font-size:.78rem}.movement {font-size:.75rem}.update-pill {float:none;text-align:center}}
</style>
""", unsafe_allow_html=True)

SUPABASE_URL = str(st.secrets.get("SUPABASE_URL", "")).rstrip("/")
SUPABASE_KEY = str(st.secrets.get("SUPABASE_PUBLISHABLE_KEY", st.secrets.get("SUPABASE_ANON_KEY", "")))
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing Supabase secrets. Set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY (or SUPABASE_ANON_KEY) in Streamlit App settings → Secrets.")
    st.stop()

@st.cache_data(ttl=300, show_spinner=False)
def get_gold_history(url, key):
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}
    all_rows = []
    offset = 0
    page_size = 1000
    while True:
        resp = requests.get(
            f"{url}/rest/v1/gold_price_history",
            headers=headers,
            params={"select": "collected_at,source_updated_at,currency,karat,price_per_gram,buy_price,sell_price", "order": "collected_at.asc", "limit": page_size, "offset": offset},
            timeout=30,
        )
        resp.raise_for_status()
        batch = resp.json()
        if not isinstance(batch, list):
            raise ValueError("Unexpected response from Supabase")
        all_rows.extend(batch)
        if len(batch) < page_size:
            break
        offset += page_size
        if offset >= 200000:
            st.warning("Showing the first 200,000 gold observations.")
            break
    return pd.DataFrame(all_rows)

@st.cache_data(ttl=900, show_spinner=False)
def get_usd_egp():
    # Public reference FX rate; not guaranteed to be a bank's buy/sell rate.
    response = requests.get("https://open.er-api.com/v6/latest/USD", timeout=20)
    response.raise_for_status()
    payload = response.json()
    if payload.get("result") != "success":
        raise ValueError("FX provider did not return a successful result")
    rate = payload.get("rates", {}).get("EGP")
    if rate is None:
        raise ValueError("EGP rate not present in FX response")
    updated = payload.get("time_last_update_utc", "Update time unavailable")
    return float(rate), updated

def format_price(value, decimals=2):
    return "—" if pd.isna(value) else f"{float(value):,.{decimals}f} EGP"

def card(label, value, change=None, is_fx=False):
    css = "flat"
    movement = "No previous update"
    if change is not None and pd.notna(change):
        if change > 0:
            css, movement = "up", f"▲ +{change:,.2f} EGP since last update"
        elif change < 0:
            css, movement = "down", f"▼ {change:,.2f} EGP since last update"
        else:
            css, movement = "flat", "● Unchanged since last update"
    st.markdown(
        f'<div class="price-card {"fx" if is_fx else ""}">'
        f'<div class="price">{html.escape(value)}</div>'
        f'<div class="price-label">{html.escape(label)}</div>'
        f'<div class="movement {css}">{html.escape(movement)}</div></div>',
        unsafe_allow_html=True,
    )

try:
