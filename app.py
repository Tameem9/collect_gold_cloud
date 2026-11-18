import html
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st

st.set_page_config(page_title="Egypt Gold & USD Tracker", page_icon="✨", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""<style>
/* Theme and app shell */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
#MainMenu, header, footer {visibility:hidden!important;}
html, body, [class*="css"], [data-testid="stApp"] {font-family:Inter,sans-serif!important;color:#1A1A1A;font-size:14px;font-variant-numeric:tabular-nums;}
[data-testid="stAppViewContainer"], [data-testid="stApp"] {background:#F7F6F3!important;}
.block-container {max-width:1120px!important;padding-top:32px!important;padding-bottom:48px!important;}
/* Typography and spacing */
h1,h2,h3,p {font-family:Inter,sans-serif!important;}
.page-title {font-size:28px;font-weight:700;line-height:1.25;letter-spacing:-.035em;color:#1A1A1A;}
.page-sub {font-size:14px;color:#5C5C5C;margin-top:8px;}
.status-line {font-size:12px;color:#8A8A8A;line-height:1.8;text-align:right;overflow-wrap:anywhere;}
.section-title {font-size:18px;font-weight:600;color:#1A1A1A;line-height:1.35;}
.section-caption {font-size:12px;color:#5C5C5C;margin:8px 0 24px;}
.field-label {font-size:12px;font-weight:500;letter-spacing:.06em;text-transform:uppercase;color:#5C5C5C;margin-bottom:8px;}
.small-note {font-size:12px;color:#5C5C5C;line-height:1.7;max-width:70ch;}
/* Responsive rate strip */
.rate-strip {display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:16px;}
@media(min-width:768px) and (max-width:1100px){.rate-strip{grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}}
@media(max-width:767px){.rate-strip{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.rate-strip .metric-number{font-size:clamp(17px,4.7vw,22px)}.rate-strip .metric-label{font-size:10px}.rate-strip .metric-change{font-size:10px;white-space:normal}}
/* Cards and sections */
.metric-card {height:150px;min-height:150px;box-sizing:border-box;background:#FFFFFF;padding:20px;border-radius:12px;box-shadow:0 1px 2px rgba(0,0,0,.04),0 4px 12px rgba(0,0,0,.04);display:flex;flex-direction:column;align-items:flex-start;justify-content:flex-start;gap:12px;overflow:hidden;}
.metric-card.featured {border-top:2px solid #B8860B;padding-top:18px;}
.metric-label {font-size:12px;font-weight:500;letter-spacing:.06em;text-transform:uppercase;color:#5C5C5C;line-height:1.4;min-height:32px;}
.metric-number {font-size:26px;font-weight:700;letter-spacing:-.035em;color:#1A1A1A;white-space:nowrap;line-height:1.1;}
.metric-unit {font-size:12px;color:#8A8A8A;font-weight:500;letter-spacing:0;}
.metric-change {font-size:12px;font-weight:500;line-height:1.4;white-space:nowrap;}
.positive {color:#2E7D4F;} .negative {color:#B4332A;} .neutral {color:#5C5C5C;}
[data-testid="stVerticalBlockBorderWrapper"] {background:#FFFFFF!important;border:0!important;border-radius:12px!important;padding:24px!important;box-shadow:0 1px 2px rgba(0,0,0,.04),0 4px 12px rgba(0,0,0,.04)!important;}
[data-testid="stVerticalBlockBorderWrapper"] > div {background:transparent!important;border:0!important;}
.section-shell {background:#FFFFFF;border-radius:12px;padding:24px;box-shadow:0 1px 2px rgba(0,0,0,.04),0 4px 12px rgba(0,0,0,.04);}
.section-gap {height:48px;}
.soft-divider {height:1px;background:#EDEBE6;margin:24px 0;}
/* Controls and segmented selections */
[data-testid="stPills"] [role="group"], [data-testid="stSegmentedControl"] [role="radiogroup"], [data-testid="stSegmentedControl"] [role="group"] {background:#EDEBE6!important;border-radius:8px!important;padding:4px!important;gap:4px!important;}
[data-testid="stPills"] button, [data-testid="stSegmentedControl"] button {border:0!important;background:transparent!important;border-radius:6px!important;color:#5C5C5C!important;font-size:12px!important;box-shadow:none!important;}
[data-testid="stPills"] button[aria-pressed="true"], [data-testid="stSegmentedControl"] button[aria-checked="true"], [data-testid="stSegmentedControl"] button[aria-pressed="true"] {background:#FFFFFF!important;color:#1A1A1A!important;box-shadow:0 1px 2px rgba(0,0,0,.08)!important;}
/* Charts and readable labels */
[data-testid="stPlotlyChart"] {background:transparent!important;}
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p, [data-testid="stWidgetLabel"] p, .stCaption {color:#5C5C5C!important;font-size:12px!important;}
/* Inputs, download actions and focus */
[data-testid="stDateInput"] input, [data-testid="stDateInput"] [data-baseweb="input"] {background:#FFFFFF!important;color:#1A1A1A!important;border-color:#E3E0DA!important;border-radius:8px!important;}
[data-testid="stDownloadButton"] button {background:#FFFFFF!important;color:#1A1A1A!important;border:1px solid #E3E0DA!important;border-radius:8px!important;font-size:14px!important;}
[data-testid="stDownloadButton"] button:hover {background:#F0EEE9!important;}
button:focus-visible,input:focus-visible,[role="radio"]:focus-visible {outline:2px solid #B8860B!important;outline-offset:2px!important;}
/* Footer and mobile layout */
.page-footer {font-size:12px;color:#8A8A8A;text-align:center;line-height:1.7;margin-top:48px;}
@media(max-width:900px){.metric-number{font-size:21px}.metric-card{padding:16px}.metric-label{font-size:11px}}
@media(max-width:767px){.block-container{padding:24px 16px 48px!important}.status-line{text-align:left;margin-top:16px}.page-title{font-size:28px}.section-shell{padding:16px}[data-testid="stVerticalBlockBorderWrapper"]{padding:16px!important}.metric-card{height:142px;min-height:142px;padding:16px}.metric-card.featured{padding-top:14px}.metric-number{font-size:22px}.metric-change{font-size:11px}.section-gap{height:32px}}
</style>""", unsafe_allow_html=True)


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
    """Try two public reference providers; never invent a price."""
    errors = []
    try:
        r = requests.get('https://open.er-api.com/v6/latest/USD', timeout=15)
        r.raise_for_status()
        payload = r.json()
        if payload.get('result') != 'success':
            raise ValueError('Provider returned an unsuccessful result')
        rate = float(payload['rates']['EGP'])
        if rate <= 0:
            raise ValueError('Invalid rate')
        updated = datetime.fromtimestamp(int(payload['time_last_update_unix']), tz=timezone.utc)
        return rate, updated.strftime('%d %b %Y · %I:%M %p UTC'), 'open.er-api.com'
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        errors.append(f'ExchangeRate-API: {exc}')
    try:
        r = requests.get('https://api.frankfurter.dev/v1/latest', params={'base':'USD', 'symbols':'EGP'}, timeout=15)
        r.raise_for_status()
        payload = r.json()
        rate = float(payload['rates']['EGP'])
        if rate <= 0:
            raise ValueError('Invalid rate')
        return rate, str(payload.get('date', 'Date unavailable')), 'frankfurter.dev'
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        errors.append(f'Frankfurter: {exc}')
    raise RuntimeError(' | '.join(errors))


@st.cache_data(ttl=300, show_spinner=False)
def load_usd_history(url, key):
    endpoint = url.rstrip('/') + '/rest/v1/usd_egp_history'
    headers = {'apikey': key, 'Authorization': f'Bearer {key}'}
    records = []
    for start in range(0, 50000, 1000):
        r = requests.get(endpoint, headers=headers,
                         params={'select':'observed_date,collected_at,provider_updated_at,usd_egp,provider',
                                 'order':'observed_date.desc','limit':1000,'offset':start}, timeout=25)
        if r.status_code in (404, 400):
            # The USD table may not have been created yet.
            return pd.DataFrame()
        r.raise_for_status()
        batch = r.json()
        records.extend(batch)
        if len(batch) < 1000:
            break
    df = pd.DataFrame.from_records(records)
    if not df.empty:
        df['observed_date'] = pd.to_datetime(df['observed_date'], errors='coerce')
        df['usd_egp'] = pd.to_numeric(df['usd_egp'], errors='coerce')
        df = df.dropna(subset=['observed_date','usd_egp']).sort_values('observed_date')
    return df


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
    usd_history = load_usd_history(SUPABASE_URL, SUPABASE_KEY)
except Exception as exc:
    usd_history = pd.DataFrame()
    st.warning(f'USD historical data could not be loaded: {exc}')

fx_error = None
try:
    fx_rate, fx_updated, fx_provider = load_fx()
    fx_note = f'{fx_updated} · {fx_provider}'
except Exception as exc:
    fx_error = str(exc)
    if not usd_history.empty:
        last_fx = usd_history.iloc[-1]
        fx_rate = float(last_fx['usd_egp'])
        fx_updated = last_fx['observed_date'].strftime('%d %b %Y')
        fx_note = f'{fx_updated} · Last stored observation'
    else:
        fx_rate, fx_updated = None, None
        fx_note = 'Reference unavailable'

# Header: timestamps remain sourced from the existing live data and provider.
header_left, header_right = st.columns([2.3, 1.5], vertical_alignment='center')
with header_left:
    st.markdown('<div class="page-title">Egypt Gold &amp; USD Tracker</div><div class="page-sub">Live reference rates, trends and history</div>', unsafe_allow_html=True)
with header_right:
    st.markdown(f'<div class="status-line">Gold updated {html.escape(last_gold_label)} Cairo<br>FX updated {html.escape(fx_note)}</div>', unsafe_allow_html=True)
st.markdown('<div style="height:32px"></div>', unsafe_allow_html=True)

# Latest gold data and prior distinct source observations: unchanged calculation.
latest_rows = gold.sort_values(['source_updated_at','collected_at']).groupby('karat').tail(1).set_index('karat')

def movement(karat):
    history = gold[gold['karat'] == karat].sort_values(['source_updated_at', 'collected_at'])
    if history.empty:
        return None, None
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

# Cards: top-aligned and equal height. The movement is from the previous distinct update,
# not necessarily the prior day's close, so the label states "since last update".
rate_cards = []
for index in range(4):
    if index < len(card_karats):
        k = card_karats[index]
        price = float(latest_rows.loc[k]['effective_sell'])
        delta, previous = movement(k)
        if delta is None:
            change = '<span class="neutral">No prior update</span>'
        elif delta > 0:
            change = f'<span class="positive">▲ {delta:,.2f} EGP since last update</span>'
        elif delta < 0:
            change = f'<span class="negative">▼ {abs(delta):,.2f} EGP since last update</span>'
        else:
            change = '<span class="neutral">No change</span>'
        label = f'{k}K gold / gram' + (' · most traded' if k == 21 else '')
        rate_cards.append(f'<div class="metric-card {"featured" if k == 21 else ""}"><div class="metric-label">{label}</div><div class="metric-number">{price:,.2f} <span class="metric-unit">EGP</span></div><div class="metric-change">{change}</div></div>')
    else:
        rate_cards.append('<div class="metric-card"><div class="metric-label">Gold / gram</div><div class="metric-number">Unavailable</div><div class="metric-change neutral">No data</div></div>')
fx_price = f'{fx_rate:,.4f}' if fx_rate is not None else 'Unavailable'
rate_cards.append(f'<div class="metric-card"><div class="metric-label">USD / EGP · reference rate</div><div class="metric-number">{fx_price} <span class="metric-unit">EGP</span></div><div class="metric-change neutral">Reference exchange rate</div></div>')

# HTML rate strip is used for responsive 5/2/2 columns without stacking full-width cards.
st.markdown('<div class="rate-strip">' + ''.join(rate_cards) + '</div>', unsafe_allow_html=True)
if fx_error and fx_rate is None:
    st.warning('USD/EGP is currently unavailable from both reference providers. ' + fx_error)
st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

# Shared chart formatting, presentation only.
def style_history_chart(fig, interval_name, line_color, ylabel, height=320):
    fig.update_layout(
        height=height, margin=dict(l=8, r=20, t=28, b=8),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif', color='#5C5C5C', size=12),
        hovermode='x unified',
        legend=dict(orientation='h', y=1.13, x=0, font=dict(color='#5C5C5C', size=12)),
        xaxis=dict(showgrid=False, tickformat={'Daily':'%b %d','Monthly':'%b %Y','Yearly':'%Y'}[interval_name],
                   linecolor='#EDEBE6', tickfont=dict(color='#8A8A8A', size=12)),
        yaxis=dict(title=ylabel, showgrid=True, gridcolor='#EDEBE6', zeroline=False,
                   tickfont=dict(color='#8A8A8A', size=12), titlefont=dict(color='#5C5C5C', size=12)),
    )
    return fig

# Gold price history, including its original selection and CSV download logic.
with st.container(border=True):
    st.markdown('<div class="section-title">Gold price history</div><div class="section-caption">One closing observation per day, month or year.</div>', unsafe_allow_html=True)
    select_col, period_col = st.columns([3, 1.25], vertical_alignment='bottom')
    with select_col:
        selected = st.pills('Karat', options=available, default=[k for k in [21] if k in available] or available[:1], selection_mode='multi', format_func=lambda k: f'{k}K')
    with period_col:
        interval = st.segmented_control('Interval', options=['Daily','Monthly','Yearly'], default='Daily')
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
        fig = go.Figure()
        palette = ['#B8860B', '#6E8C75', '#8E7596', '#9E6F54', '#527E91']
        for i, k in enumerate(selected):
            df = plotted[plotted['karat'] == k]
            color = palette[i % len(palette)]
            fig.add_trace(go.Scatter(x=df['period'], y=df['effective_sell'], name=f'{k}K gold',
                mode='lines+markers', line=dict(color=color, width=2), marker=dict(size=5),
                fill='tozeroy' if len(selected) == 1 else None,
                fillcolor='rgba(184,134,11,0.08)' if len(selected) == 1 else None,
                hovertemplate='%{x|%b %d, %Y}<br><b>%{y:,.2f} EGP</b><extra>%{fullData.name}</extra>'))
            if len(df):
                last = df.iloc[-1]
                fig.add_annotation(x=last['period'], y=last['effective_sell'],
                    text=f"{last['effective_sell']:,.2f}", showarrow=False, yshift=18,
                    font=dict(size=12, color=color), bgcolor='#FFFFFF')
        style_history_chart(fig, interval, '#B8860B', 'EGP per gram')
        fig.update_yaxes(tickformat=',.0f')
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})
        if len(plotted) == 1:
            st.caption('Only one observation so far. The line will appear as more days are collected.')
        st.markdown('<div class="small-note">Historical prices use sell_price where available, otherwise price_per_gram. Each period shows its last recorded observation. Times are grouped by Cairo local date.</div>', unsafe_allow_html=True)
    st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)
    min_date = gold['collected_at'].dt.tz_convert('Africa/Cairo').min().date()
    max_date = gold['collected_at'].dt.tz_convert('Africa/Cairo').max().date()
    d1, d2, d3 = st.columns([1, 1, 1], vertical_alignment='bottom')
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
        with d3:
            st.download_button('Download CSV', data=export.to_csv(index=False).encode('utf-8-sig'),
                file_name=f'egypt_gold_{start}_{end}.csv', mime='text/csv', disabled=export.empty, use_container_width=True)
        st.caption(f'{len(export):,} records available for download · No table displayed')
st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)

# USD / EGP history, with its original interval and export logic.
with st.container(border=True):
    st.markdown('<div class="section-title">USD / EGP history</div><div class="section-caption">Historical USD exchange rates in Egyptian pounds. One stored observation per day.</div>', unsafe_allow_html=True)
    if usd_history.empty:
        st.info('No stored USD/EGP history yet. Create the Supabase USD table and run the USD collector once in GitHub Actions. The chart will populate as observations accumulate.')
    else:
        _, fx_control = st.columns([3, 1.25])
        with fx_control:
            fx_interval = st.segmented_control('Interval', options=['Daily','Monthly','Yearly'], default='Daily', key='fx_interval')
        fx_period = usd_history.copy()
        fx_period['period'] = fx_period['observed_date'].dt.to_period({'Daily':'D','Monthly':'M','Yearly':'Y'}[fx_interval]).dt.to_timestamp()
        fx_period = fx_period.groupby('period', as_index=False).tail(1).sort_values('period')
        fx_fig = go.Figure()
        fx_fig.add_trace(go.Scatter(x=fx_period['period'], y=fx_period['usd_egp'], name='USD / EGP',
            mode='lines+markers', line=dict(color='#2F5D8A', width=2), marker=dict(size=6),
            fill='tozeroy', fillcolor='rgba(47,93,138,0.08)',
            hovertemplate='<b>%{x|%d %b %Y}</b><br>USD/EGP: %{y:,.4f} EGP<extra></extra>'))
        if len(fx_period):
            last = fx_period.iloc[-1]
            fx_fig.add_annotation(x=last['period'], y=last['usd_egp'],
                text=f"{last['usd_egp']:,.4f}", showarrow=False, yshift=18,
                font=dict(size=12, color='#2F5D8A'), bgcolor='#FFFFFF')
        style_history_chart(fx_fig, fx_interval, '#2F5D8A', 'EGP per USD')
        fx_fig.update_yaxes(tickformat=',.2f')
        st.plotly_chart(fx_fig, use_container_width=True, config={'displayModeBar':False})
        if len(fx_period) == 1:
            st.caption('Only one observation so far. The line will appear as more days are collected.')
        st.markdown('<div class="small-note">Daily snapshots are stored by the GitHub Actions USD collector. Monthly and yearly views show the last stored rate in each period.</div>', unsafe_allow_html=True)
    st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)
    if usd_history.empty:
        st.caption('The download becomes available after the first USD collection.')
    else:
        fx_min = usd_history['observed_date'].min().date()
        fx_max = usd_history['observed_date'].max().date()
        fx_d1, fx_d2, fx_d3 = st.columns([1, 1, 1], vertical_alignment='bottom')
        with fx_d1:
            fx_start = st.date_input('From', value=max(fx_min, fx_max-timedelta(days=365)), min_value=fx_min, max_value=fx_max, key='fx_from')
        with fx_d2:
            fx_end = st.date_input('To', value=fx_max, min_value=fx_min, max_value=fx_max, key='fx_to')
        if fx_start > fx_end:
            st.warning('The start date must be on or before the end date.')
        else:
            export_fx = usd_history[(usd_history['observed_date'].dt.date >= fx_start) &
                                    (usd_history['observed_date'].dt.date <= fx_end)]
            with fx_d3:
                st.download_button('Download CSV', data=export_fx.to_csv(index=False).encode('utf-8-sig'),
                    file_name=f'usd_egp_{fx_start}_{fx_end}.csv', mime='text/csv', disabled=export_fx.empty, use_container_width=True)
            st.caption(f'{len(export_fx):,} daily observations available · Raw table hidden')

st.markdown('<div class="page-footer">Gold data: Supabase gold collector · FX: ExchangeRate-API / Frankfurter reference providers and your Supabase USD collector.<br>Reference rates may differ from Egyptian bank buy/sell quotes. Dates are grouped by Cairo local time.</div>', unsafe_allow_html=True)
