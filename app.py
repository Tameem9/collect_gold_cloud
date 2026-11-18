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
    gold = get_gold_history(SUPABASE_URL, SUPABASE_KEY)
except Exception as exc:
    st.error(f"Could not load gold data from Supabase: {exc}")
    st.stop()

if gold.empty:
    st.warning("No gold history found in Supabase yet. Check the collector and the table's read policy.")
    st.stop()

for col in ["price_per_gram", "buy_price", "sell_price", "karat"]:
    gold[col] = pd.to_numeric(gold[col], errors="coerce")
for col in ["collected_at", "source_updated_at"]:
    gold[col] = pd.to_datetime(gold[col], errors="coerce", utc=True)
gold = gold.dropna(subset=["collected_at", "karat"]).sort_values("collected_at")
gold["karat"] = gold["karat"].astype(int)
# Use the higher (sell) quote where available; fall back to price_per_gram.
gold["chart_price"] = gold["sell_price"].fillna(gold["price_per_gram"])
gold = gold.dropna(subset=["chart_price"])
if gold.empty:
    st.error("No valid gold prices are available in the database.")
    st.stop()

try:
    fx_rate, fx_updated = get_usd_egp()
except Exception:
    fx_rate, fx_updated = None, "Currently unavailable"

st.markdown(f'<div class="update-pill">🕒 FX reference last updated<br><strong>{html.escape(str(fx_updated))}</strong></div>', unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>Egypt Gold &amp; USD Tracker</h1><p>Live gold prices and historical trends in Egyptian pounds</p></div>', unsafe_allow_html=True)

available_karats = sorted(gold["karat"].unique(), reverse=True)
# Five symmetric cards: 4 gold karats + USD/EGP.
preferred = [24, 21, 18, 14]
card_karats = [k for k in preferred if k in available_karats]
card_karats += [k for k in available_karats if k not in card_karats][:max(0, 4 - len(card_karats))]
card_karats = card_karats[:4]

columns = st.columns(5, gap="small")
for i in range(4):
    with columns[i]:
        if i >= len(card_karats):
            card("Gold", "—")
            continue
        k = card_karats[i]
        rows = gold.loc[gold["karat"] == k].sort_values(["source_updated_at", "collected_at"])
        # Multiple collections of the same source timestamp should not count as new prices.
        rows = rows.drop_duplicates(subset=["source_updated_at"], keep="last")
        if len(rows) < 2:
            # If source timestamp is missing, fall back to distinct collected observations.
            rows = gold.loc[gold["karat"] == k].sort_values("collected_at").drop_duplicates(subset=["chart_price"], keep="last")
        current = float(rows.iloc[-1]["chart_price"])
        previous = float(rows.iloc[-2]["chart_price"]) if len(rows) > 1 else None
        card(f"{k}K Gold", format_price(current), None if previous is None else current - previous)
with columns[4]:
    card("USD / EGP", format_price(fx_rate, 4) if fx_rate is not None else "Unavailable", is_fx=True)

st.caption("Gold changes compare the latest recorded source update with the previous one (not necessarily one hour ago). USD/EGP is a reference exchange rate, not a bank quote.")
st.divider()
st.subheader("📈 Gold price history")

# Karat selection via visible toggle buttons instead of a dropdown.
if "selected_karats" not in st.session_state:
    st.session_state.selected_karats = [21] if 21 in available_karats else available_karats[:1]
st.write("**Choose gold karats**")
buttons = st.columns(len(available_karats))
for i, k in enumerate(available_karats):
    with buttons[i]:
        selected = k in st.session_state.selected_karats
        if st.button(f"{'✓ ' if selected else ''}{k}K", key=f"karat_{k}", use_container_width=True, type="primary" if selected else "secondary"):
            if selected:
                st.session_state.selected_karats = [v for v in st.session_state.selected_karats if v != k]
            else:
                st.session_state.selected_karats = sorted(st.session_state.selected_karats + [k], reverse=True)
            st.rerun()

period = st.segmented_control("Time grouping", ["Daily", "Monthly", "Yearly"], default="Daily")
selected_karats = st.session_state.selected_karats
if not selected_karats:
    st.info("Select at least one karat to view its history.")
else:
    filtered = gold.loc[gold["karat"].isin(selected_karats)].copy()
    # The daily/monthly/yearly value is the last available sell quote for each period.
    if period == "Monthly":
        filtered["period"] = filtered["collected_at"].dt.tz_convert("Africa/Cairo").dt.strftime("%Y-%m")
    elif period == "Yearly":
        filtered["period"] = filtered["collected_at"].dt.tz_convert("Africa/Cairo").dt.strftime("%Y")
    else:
        filtered["period"] = filtered["collected_at"].dt.tz_convert("Africa/Cairo").dt.strftime("%Y-%m-%d")
    daily = filtered.sort_values("collected_at").groupby(["period", "karat"], as_index=False).tail(1)
    chart = daily.pivot(index="period", columns="karat", values="chart_price").sort_index()
    chart.columns = [f"{int(k)}K Gold" for k in chart.columns]
    st.line_chart(chart, x_label="Date", y_label="EGP per gram", use_container_width=True)
    st.caption("One value per selected period: the last recorded sell price (or the standard gram price if sell price is unavailable).")

st.divider()
st.subheader("⬇️ Download gold history")
min_date = gold["collected_at"].dt.tz_convert("Africa/Cairo").dt.date.min()
max_date = gold["collected_at"].dt.tz_convert("Africa/Cairo").dt.date.max()
range_dates = st.date_input("Choose dates to export", value=(min_date, max_date), min_value=min_date, max_value=max_date)
if len(range_dates) == 2:
    start_date, end_date = range_dates
    export = gold.loc[gold["karat"].isin(selected_karats)].copy()
    cairo_dates = export["collected_at"].dt.tz_convert("Africa/Cairo").dt.date
    export = export.loc[(cairo_dates >= start_date) & (cairo_dates <= end_date)]
    export = export[["collected_at", "source_updated_at", "currency", "karat", "price_per_gram", "buy_price", "sell_price"]]
    st.download_button(
        "Download selected gold history (CSV)",
        data=export.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"egypt_gold_history_{start_date}_{end_date}.csv",
        mime="text/csv", use_container_width=True,
        disabled=export.empty,
    )
    if export.empty:
        st.caption("No records match the selected karats and dates.")
else:
    st.caption("Choose both a start and end date to download.")
