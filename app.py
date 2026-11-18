# Compare the two latest distinct source updates per karat, not repeated collection runs.
# This means the arrow compares against the previous recorded price, regardless of elapsed time.
latest = gold.sort_values("collected_at").groupby("karat").tail(1).set_index("karat")
previous_prices = {}
for karat, frame in gold.groupby("karat"):
    frame = frame.sort_values("collected_at").drop_duplicates(subset=["source_updated_at"], keep="last")
    if len(frame) >= 2:
        previous_prices[karat] = float(frame.iloc[-2]["display_price"])

try:
    usd_rate, fx_updated = get_usd()
except Exception:
    usd_rate, fx_updated = None, "Unavailable"

st.markdown(f'<div class="fx-updated"><div><small>FX reference last updated</small><strong>{html.escape(str(fx_updated))}</strong></div></div>', unsafe_allow_html=True)
st.markdown('<div class="main-heading">Egypt Gold &amp; USD Tracker</div>', unsafe_allow_html=True)
st.markdown('<div class="main-subtitle">Egyptian gold prices and USD / EGP reference rate</div>', unsafe_allow_html=True)

cards = []
for karat in [24, 22, 21, 18]:
    if karat in latest.index:
        current = float(latest.loc[karat, "display_price"])
        price = f"{current:,.2f}"
        prior = previous_prices.get(karat)
        if prior is None:
            change, cls = "— No earlier update", "flat"
        else:
            difference = current - prior
            if difference > 0:
                change, cls = f"▲ +{difference:,.2f} EGP", "up"
            elif difference < 0:
                change, cls = f"▼ {difference:,.2f} EGP", "down"
            else:
                change, cls = "→ No change", "flat"
    else:
        price, change, cls = "—", "— No data", "flat"
    cards.append((price, f"{karat}K Gold", "EGP / gram", change, cls, False))
# The FX API supplies only the current reference rate. Do not fabricate an earlier rate.
cards.append((f"{usd_rate:,.4f}" if usd_rate is not None else "—", "USD / EGP", "EGP", "— Previous FX rate unavailable", "flat", True))
markup = '<div class="price-grid">'
for price, label, unit, change, cls, is_fx in cards:
    fx_class = " fx-card" if is_fx else ""
    markup += (f'<div class="price-card{fx_class}"><div class="price-value">{html.escape(price)}</div>'
               f'<div class="price-label">{html.escape(label)}</div>'
               f'<div class="price-unit">{html.escape(unit)}</div>'
               f'<div class="price-change {cls}">{html.escape(change)}</div></div>')
markup += '</div>'

st.markdown(markup, unsafe_allow_html=True)
st.caption("▲/▼ compares each karat with its previous distinct recorded source update (not necessarily one hour ago). Gold uses sell prices when available. USD/EGP arrows will require historical FX collection.")

st.subheader("Gold price history")
available = sorted(gold["karat"].astype(int).unique().tolist(), reverse=True)
selected = st.pills("Select karats", options=available, default=available, selection_mode="multi", format_func=lambda k: f"{k}K")
period = st.segmented_control("Time grouping", ["Daily", "Monthly", "Yearly"], default="Daily")

if selected:
    chosen = gold[gold["karat"].isin(selected)].copy()
    chosen["Karat"] = chosen["karat"].astype(int).astype(str) + "K"
    if period == "Daily":
        chosen["period"] = chosen["local_time"].dt.strftime("%Y-%m-%d")
    elif period == "Monthly":
        chosen["period"] = chosen["local_time"].dt.strftime("%Y-%m")
    else:
        chosen["period"] = chosen["local_time"].dt.strftime("%Y")

    # Last observed sell price in each Cairo-local day/month/year (not hourly points).
    daily = (chosen.sort_values("collected_at")
             .groupby(["Karat", "period"], as_index=False).tail(1)
             .sort_values(["period", "Karat"]))
    fig = px.line(daily, x="period", y="display_price", color="Karat", markers=True,
                  labels={"period": "Date" if period == "Daily" else "Period",
                          "display_price": "EGP per gram"})
    fig.update_layout(legend_title_text="Karat", hovermode="x unified", margin=dict(l=10,r=10,t=15,b=10))
    fig.update_xaxes(type="category", title="Date" if period == "Daily" else "Period")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"One observation per { {'Daily': 'day', 'Monthly': 'month', 'Yearly': 'year'}[period]}: last available sell price in Egypt local time. Missing dates are not filled.")
else:
    st.info("Choose at least one karat to view its history.")

st.subheader("Download gold price history")
min_date = gold["local_date"].min()
max_date = gold["local_date"].max()
start_default = max(min_date, max_date - timedelta(days=365))
from_col, to_col = st.columns(2)
with from_col:
    start_date = st.date_input("From", value=start_default, min_value=min_date, max_value=max_date)
with to_col:
    end_date = st.date_input("To", value=max_date, min_value=min_date, max_value=max_date)

if start_date > end_date:
    st.warning("The start date must be on or before the end date.")
else:
    export = gold[(gold["local_date"] >= start_date) & (gold["local_date"] <= end_date)].copy()
    if selected:
        export = export[export["karat"].isin(selected)]
    else:
        export = export.iloc[0:0]
    export = export.sort_values("collected_at")
    export["egypt_time"] = export["local_time"].dt.strftime("%Y-%m-%d %H:%M:%S %Z")
    columns = ["egypt_time", "karat", "currency", "display_price", "price_per_gram", "buy_price", "sell_price", "source_updated_at"]
    csv = export[columns].to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇ Download selected gold history (CSV)", data=csv,
                       file_name=f"egypt_gold_{start_date}_{end_date}.csv", mime="text/csv",
                       disabled=export.empty, use_container_width=True)
    st.caption(f"{len(export):,} records ready to download. Raw observations are exported without displaying a table.")

st.caption("Gold history starts when your collector began. Historical USD/EGP data needs a separate scheduled FX collector; this version shows the latest reference rate only.")
