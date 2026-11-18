
import os
import requests
from datetime import datetime, timezone

GOLD_API_KEY = os.environ["GOLD_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

# Get Egyptian gold prices
response = requests.get(
    "https://goldapi.dev/api/v1/karat",
    headers={"X-API-Key": GOLD_API_KEY},
    params={"currency": "EGP"},
    timeout=30
)
response.raise_for_status()
data = response.json()

if data.get("currency") != "EGP":
    raise ValueError("Unexpected currency")

if not data.get("karats"):
    raise ValueError("No gold prices returned")

# Prepare records
collected_at = datetime.now(timezone.utc).isoformat()
source_updated_at = data.get("updatedAt")

if not source_updated_at:
    raise ValueError("Missing source update timestamp")

rows = []

for item in data["karats"]:
    rows.append({
        "collected_at": collected_at,
        "source_updated_at": source_updated_at,
        "currency": "EGP",
        "karat": item["karat"],
        "price_per_gram": item["gram"],
        "buy_price": item.get("gramBuy"),
        "sell_price": item.get("gramSell")
    })

# Save to Supabase
result = requests.post(
    f"{SUPABASE_URL}/rest/v1/gold_price_history",
    headers={
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates,return=minimal"
    },
    params={
        "on_conflict": "source_updated_at,currency,karat"
    },
    json=rows,
    timeout=30
)
if not result.ok:
    print("Supabase HTTP status:", result.status_code)
    print("Supabase error details:", result.text[:1000])
    result.raise_for_status()

print(f"Cloud collection completed for {len(rows)} karats")
