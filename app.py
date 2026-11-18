import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title='Egypt Gold & USD Tracker', page_icon='🥇', layout='wide')
st.title('🥇 Egyptian Gold & USD Tracker')
st.caption('Historical gold prices from Supabase · USD/EGP spot reference')

try:
    url = st.secrets['SUPABASE_URL'].rstrip('/')
    key = st.secrets['SUPABASE_PUBLISHABLE_KEY']
except KeyError:
    st.error('Configure SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY in Streamlit app secrets.')
    st.stop()

@st.cache_data(ttl=300)
def get_gold():
    rows = []
    offset = 0
    while True:
        response = requests.get(
            f'{url}/rest/v1/gold_price_history',
            headers={'apikey': key, 'Authorization': f'Bearer {key}'},
            params={'select': 'karat,currency,price_per_gram,buy_price,sell_price,collected_at,source_updated_at',
                    'order': 'collected_at.desc', 'limit': 1000, 'offset': offset},
            timeout=30,
        )
        response.raise_for_status()
        batch = response.json()
        rows.extend(batch)
        if len(batch) < 1000:
            break
        offset += 1000
    return pd.DataFrame(rows)

@st.cache_data(ttl=3600)
def get_usd():
    # Public reference feed; availability and methodology may differ from bank rates.
    response = requests.get('https://open.er-api.com/v6/latest/USD', timeout=20)
    response.raise_for_status()
    payload = response.json()
    if payload.get('result') != 'success':
        raise ValueError('FX provider returned an unsuccessful response')
    return float(payload['rates']['EGP']), payload.get('time_last_update_utc', 'Unknown')

try:
    df = get_gold()
except Exception as exc:
    st.error(f'Unable to read gold history from Supabase: {exc}')
    st.stop()

if df.empty:
    st.warning('No gold prices found. Verify collector inserts and Supabase read permissions.')
    st.stop()

df['collected_at'] = pd.to_datetime(df['collected_at'], utc=True, errors='coerce')
df['source_updated_at'] = pd.to_datetime(df['source_updated_at'], utc=True, errors='coerce')
for col in ['karat', 'price_per_gram', 'buy_price', 'sell_price']:
    df[col] = pd.to_numeric(df[col], errors='coerce')
df = df.dropna(subset=['karat', 'collected_at', 'price_per_gram'])
df = df[df['currency'] == 'EGP'].sort_values('collected_at')
if df.empty:
    st.warning('No valid EGP gold observations available.')
    st.stop()

latest = df.sort_values('collected_at').groupby('karat', as_index=False).tail(1)
cols = st.columns(min(len(latest), 4))
for i, (_, r) in enumerate(latest.sort_values('karat', ascending=False).iterrows()):
    with cols[i % len(cols)]:
        st.metric(f'{int(r.karat)}K Gold', f'{r.price_per_gram:,.2f} EGP/g')

st.subheader('USD / EGP')
try:
    rate, updated = get_usd()
    st.metric('1 USD', f'{rate:,.4f} EGP')
    st.caption(f'FX reference last updated: {updated}. Not a bank buy/sell quotation.')
except Exception:
    st.info('USD/EGP reference is temporarily unavailable. Gold history is unaffected.')

st.subheader('Gold price history')
karats = sorted(df.karat.unique().tolist(), reverse=True)
selected = st.multiselect('Select karats', karats, default=karats, format_func=lambda x: f'{int(x)}K')
metric = st.selectbox('Price series', ['price_per_gram', 'buy_price', 'sell_price'], format_func=lambda x: x.replace('_', ' ').title())
filtered = df[df.karat.isin(selected)].dropna(subset=[metric]).copy()
filtered['Karat'] = filtered['karat'].astype(int).astype(str) + 'K'
if not filtered.empty:
    fig = px.line(filtered, x='collected_at', y=metric, color='Karat', markers=True,
                  labels={'collected_at': 'Collection time (UTC)', metric: 'EGP per gram'})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info('No data for this selection.')

st.subheader('Historical records')
st.dataframe(filtered.sort_values('collected_at', ascending=False), use_container_width=True, hide_index=True)
st.download_button('Download selected gold history (CSV)', filtered.to_csv(index=False).encode('utf-8'),
                   file_name='egypt_gold_history.csv', mime='text/csv')
st.caption('Gold history begins when your collector started. USD/EGP history requires a separate scheduled collector.')
