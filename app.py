import html
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="Egypt Gold & USD Tracker", page_icon="✨", layout="wide", initial_sidebar_state="collapsed")

st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], [data-testid="stApp"] {font-family:'DM Sans',sans-serif;}
[data-testid="stAppViewContainer"] {background:#f2f3f6;}
.block-container {max-width:1450px; padding-top:2rem; padding-bottom:3rem;}
[data-testid="stHeader"] {background:transparent;}
h1,h2,h3 {color:#20243b;}
.hero-title {text-align:center;font-weight:800;font-size:clamp(2rem,4vw,3.1rem);letter-spacing:-1.5px;color:#20243b;margin:0;}
.hero-sub {text-align:center;color:#85899b;font-size:.96rem;margin:.25rem 0 1.7rem;}
.fx-status {background:white;border:1px solid #e6e8f0;border-radius:13px;padding:12px 18px;display:inline-block;box-shadow:0 3px 12px #26334a08;}
.fx-status .eyebrow {font-size:.72rem;color:#8b91a2;font-weight:700;letter-spacing:.04em;}
.fx-status .stamp {font-size:.86rem;color:#30364b;font-weight:700;}
.metric-card {background:white;border:1px solid #e9eaf1;border-radius:19px;min-height:158px;box-shadow:0 6px 24px #232b4609;padding:22px 10px 16px;text-align:center;display:flex;flex-direction:column;justify-content:center;align-items:center;}
.metric-card.usd {background:#fffdf6;border-color:#f0e4c4;}
.metric-number {font-size:clamp(1.05rem,1.65vw,1.65rem);font-weight:800;color:#22263b;letter-spacing:-.6px;white-space:nowrap;}
.metric-label {font-size:.84rem;color:#737b8f;font-weight:700;margin-top:7px;}
.metric-change {font-size:.77rem;margin-top:10px;font-weight:700;}
.positive {color:#10a77a;} .negative {color:#ed6176;} .neutral {color:#9ca1ae;}
.section-head {font-weight:800;font-size:1.13rem;color:#24283c;margin:8px 0 4px;}
.section-sub {font-size:.82rem;color:#9298a8;margin-bottom:8px;}
[data-testid="stVerticalBlockBorderWrapper"] {background:#ffffff!important;border-radius:18px!important;border:1px solid #e7e9f0!important;box-shadow:0 5px 20px #232b4608!important;}
[data-testid="stVerticalBlockBorderWrapper"] > div {border-radius:18px!important;}
[data-testid="stPlotlyChart"] {border-radius:16px;}
.stButton button {border-radius:11px;}
[data-testid="stDownloadButton"] button {background:#292b6b;color:white;border:0;border-radius:11px;}
</style>''', unsafe_allow_html=True)


def secret_value(*names):
    for name in names:
        try:
            val = st.secrets.get(name)
            if val:
                return str(val)
        except Exception:
            pass
    return None

SUPABASE_URL = secret_value("SUPABASE_URL")
SUPABASE_KEY = secret_value("SUPABASE_PUBLISHABLE_KEY", "SUPABASE_ANON_KEY", "SUPABASE_KEY")
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Missing Streamlit secrets: SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY (or SUPABASE_ANON_KEY).")
    st.stop()


@st.cache_data(ttl=300, show_spinner=False)
def load_gold(url, key):
    endpoint = url.rstrip('/') + '/rest/v1/gold_price_history'
    headers = {'apikey': key, 'Authorization': f'Bearer {key}'}
    records = []
    page_size = 1000
    # Paginate to avoid the Supabase/PostgREST default 1,000-row limit.
    for start in range(0, 100000, page_size):
        response = requests.get(endpoint, headers=headers, params={
            'select': 'collected_at,source_updated_at,currency,karat,price_per_gram,buy_price,sell_price',
            'order': 'collected_at.desc', 'limit': page_size, 'offset': start
        }, timeout=25)
        response.raise_for_status()
        batch = response.json()
        records.extend(batch)
        if len(batch) < page_size:
            break
    return pd.DataFrame.from_records(records)


@st.cache_data(ttl=900, show_spinner=False)
def load_fx():
    # Public reference rate, not a bank-specific or cash-market quote.
    response = requests.get('https://api.frankfurter.dev/v1/latest', params={'base':'USD', 'symbols':'EGP'}, timeout=15)
    response.raise_for_status()
    payload = response.json()
    return float(payload['rates']['EGP']), str(payload.get('date', 'Date unavailable'))


try:
    gold = load_gold(SUPABASE_URL, SUPABASE_KEY)
except Exception as exc:
    st.error(f"Could not read gold history from Supabase: {exc}")
    st.stop()

if gold.empty:
    st.warning('Supabase returned no gold prices. Check your read-only policy and collector.')
    st.stop()

for col in ('collected_at', 'source_updated_at'):
    if col in gold:
        gold[col] = pd.to_datetime(gold[col], errors='coerce', utc=True)
for col in ('price_per_gram', 'buy_price', 'sell_price', 'karat'):
    gold[col] = pd.to_numeric(gold[col], errors='coerce')
gold = gold.dropna(subset=['collected_at', 'karat']).sort_values('collected_at')
gold['karat'] = gold['karat'].astype(int)
gold['effective_sell'] = gold['sell_price'].fillna(gold['price_per_gram'])
gold = gold.dropna(subset=['effective_sell'])

# Latest gold data timestamp from the actual collector records (Cairo local time).
last_gold_update = gold['source_updated_at'].dropna().max()
if pd.isna(last_gold_update):
    last_gold_update = gold['collected_at'].max()
last_gold_label = last_gold_update.tz_convert('Africa/Cairo').strftime('%d %b %Y · %I:%M %p') if pd.notna(last_gold_update) else 'Unavailable'

try:
    fx_rate, fx_updated = load_fx()
    fx_note = f'USD/EGP reference · {fx_updated}'
except Exception:
    fx_rate, fx_updated = None, None
    fx_note = 'USD/EGP reference unavailable'

# Both update stamps are visible in the header. FX date is provider-supplied, not a live timestamp.
left, right = st.columns([1, 1])
with left:
    st.markdown(f'<div class="fx-status"><div class="eyebrow">GOLD LAST UPDATED · CAIRO</div><div class="stamp">{html.escape(last_gold_label)}</div></div>', unsafe_allow_html=True)
with right:
    st.markdown(f'<div style="text-align:right"><div class="fx-status"><div class="eyebrow">FX REFERENCE LAST UPDATED</div><div class="stamp">{html.escape(fx_note)}</div></div></div>', unsafe_allow_html=True)
st.markdown('<div class="hero-title">Egypt Gold &amp; USD Tracker</div><div class="hero-sub">Live reference rates · Gold market trends · Historical insights</div>', unsafe_allow_html=True)

# Most recent distinct prices by karat, with prior distinct snapshot for comparison.
latest_rows = gold.sort_values(['source_updated_at','collected_at']).groupby('karat').tail(1).set_index('karat')

def movement(karat):
    history = gold[gold['karat'] == karat].sort_values(['source_updated_at', 'collected_at'])
    if history.empty:
        return None, None
    # Ignore collector duplicates of the same source timestamp and price.
    history = history.drop_duplicates(subset=['source_updated_at', 'effective_sell'], keep='last')
    if len(history) < 2:
        return None, None
    current = float(history.iloc[-1]['effective_sell'])
    previous = float(history.iloc[-2]['effective_sell'])
    return current - previous, previous

available = sorted(gold['karat'].unique(), reverse=True)
preferred = [24, 21, 18, 14]
card_karats = [k for k in preferred if k in available]
card_karats += [k for k in available if k not in card_karats][:max(0, 4-len(card_karats))]
card_karats = card_karats[:4]

cards = st.columns(5, gap='small')
for index in range(5):
    with cards[index]:
        if index < 4:
            if index < len(card_karats):
                k = card_karats[index]
                price = float(latest_rows.loc[k]['effective_sell'])
                delta, previous = movement(k)
                if delta is None:
                    change = '<span class="neutral">— No prior update</span>'
                elif delta > 0:
                    change = f'<span class="positive">▲ +{delta:,.2f} EGP</span>'
                elif delta < 0:
                    change = f'<span class="negative">▼ {delta:,.2f} EGP</span>'
                else:
                    change = '<span class="neutral">● Unchanged</span>'
                content = f'<div class="metric-number">{price:,.2f} <span style="font-size:.66em;color:#8c91a0">EGP</span></div><div class="metric-label">{k}K Gold / gram</div><div class="metric-change">{change}</div>'
            else:
                content = '<div class="metric-number">—</div><div class="metric-label">Gold</div><div class="metric-change neutral">No data</div>'
            st.markdown(f'<div class="metric-card">{content}</div>', unsafe_allow_html=True)
        else:
            price = f'{fx_rate:,.4f}' if fx_rate is not None else '—'
            st.markdown(f'<div class="metric-card usd"><div class="metric-number">{price} <span style="font-size:.66em;color:#8c91a0">EGP</span></div><div class="metric-label">USD / EGP</div><div class="metric-change neutral">Reference exchange rate</div></div>', unsafe_allow_html=True)

st.write('')
with st.container(border=True):
    st.markdown('<div class="section-head">Gold price history</div><div class="section-sub">Choose karats and a time interval. One closing observation is shown per day, month or year.</div>', unsafe_allow_html=True)
    select_col, period_col = st.columns([3, 1.25], vertical_alignment='bottom')
    with select_col:
        selected = st.pills('Gold karats', options=available, default=[k for k in [21] if k in available] or available[:1], selection_mode='multi', format_func=lambda k: f'{k}K')
    with period_col:
        interval = st.segmented_control('Time interval', options=['Daily','Monthly','Yearly'], default='Daily')
    if not selected:
        st.info('Select at least one karat to display the chart.')
    else:
        selected_gold = gold[gold['karat'].isin(selected)].copy()
        selected_gold['local_date'] = selected_gold['collected_at'].dt.tz_convert('Africa/Cairo').dt.tz_localize(None)
        period_rule = {'Daily':'D', 'Monthly':'MS', 'Yearly':'YS'}[interval]
        selected_gold['period'] = selected_gold['local_date'].dt.to_period({'Daily':'D','Monthly':'M','Yearly':'Y'}[interval]).dt.to_timestamp()
        plotted = (selected_gold.sort_values('collected_at')
                   .groupby(['karat','period'], as_index=False).tail(1)
                   .sort_values('period'))
        palette = ['#4cc3d9', '#6762d8', '#f49d56', '#11b995', '#e7678a']
        fig = go.Figure()
        for i, k in enumerate(selected):
            df = plotted[plotted['karat'] == k]
            fig.add_trace(go.Scatter(x=df['period'], y=df['effective_sell'], name=f'{k}K Gold', mode='lines+markers',
                                     line=dict(color=palette[i % len(palette)], width=3),
                                     marker=dict(size=6),
                                     hovertemplate='%{x|%b %d, %Y}<br><b>%{y:,.2f} EGP</b><extra>%{fullData.name}</extra>'))
        fig.update_layout(height=390, margin=dict(l=10,r=15,t=25,b=15),
                          paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF',
                          font=dict(family='DM Sans, sans-serif', color='#737b90', size=12),
                          hovermode='x unified', legend=dict(orientation='h', y=1.12, x=0),
                          xaxis=dict(showgrid=False, tickformat={'Daily':'%b %d','Monthly':'%b %Y','Yearly':'%Y'}[interval],
                                     linecolor='#e5e7ed'),
                          yaxis=dict(title='EGP per gram', showgrid=True, gridcolor='#e9ebf1', zeroline=False, tickformat=',.0f'))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
        st.caption('Historical prices use sell_price where available, otherwise price_per_gram. Each period shows its last recorded observation. Times are grouped by Cairo local date.')

with st.container(border=True):
    st.markdown('<div class="section-head">Download gold history</div><div class="section-sub">Choose a date range and download your selected karats. Raw records stay hidden.</div>', unsafe_allow_html=True)
    min_date = gold['collected_at'].dt.tz_convert('Africa/Cairo').min().date()
    max_date = gold['collected_at'].dt.tz_convert('Africa/Cairo').max().date()
    d1, d2 = st.columns(2)
    with d1:
        start = st.date_input('From', value=max(min_date, max_date - timedelta(days=365)), min_value=min_date, max_value=max_date)
    with d2:
        end = st.date_input('To', value=max_date, min_value=min_date, max_value=max_date)
    if start > end:
        st.warning('The start date must be on or before the end date.')
    else:
        chosen = selected if selected else available
        export = gold[gold['karat'].isin(chosen)].copy()
        local_dates = export['collected_at'].dt.tz_convert('Africa/Cairo').dt.date
        export = export[(local_dates >= start) & (local_dates <= end)]
        export = export[['collected_at','source_updated_at','currency','karat','price_per_gram','buy_price','sell_price']]
        st.download_button('↓ Download selected gold history (CSV)', data=export.to_csv(index=False).encode('utf-8-sig'),
                           file_name=f'egypt_gold_{start}_{end}.csv', mime='text/csv', disabled=export.empty)
        st.caption(f'{len(export):,} records available for download · No table displayed')

st.caption('Gold data: your Supabase collector · FX: Frankfurter reference API. FX is a reference rate, not necessarily a local bank buy/sell quote.')
