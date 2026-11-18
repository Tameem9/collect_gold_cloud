"""Collect USD/EGP once per day into Supabase; run via GitHub Actions."""
import os
from datetime import datetime, timezone
import requests


def fetch_rate():
    errors = []
    try:
        r = requests.get('https://open.er-api.com/v6/latest/USD', timeout=25)
        r.raise_for_status()
        p = r.json()
        if p.get('result') != 'success':
            raise ValueError('ExchangeRate-API did not return success')
        rate = float(p['rates']['EGP'])
        if rate <= 0:
            raise ValueError('Invalid USD/EGP rate')
        updated = datetime.fromtimestamp(int(p['time_last_update_unix']), tz=timezone.utc).isoformat()
        return rate, updated, 'open.er-api.com'
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    try:
        r = requests.get('https://api.frankfurter.dev/v1/latest', params={'base':'USD','symbols':'EGP'}, timeout=25)
        r.raise_for_status()
        p = r.json()
        rate = float(p['rates']['EGP'])
        if rate <= 0:
            raise ValueError('Invalid USD/EGP rate')
        return rate, str(p['date']) + 'T00:00:00+00:00', 'frankfurter.dev'
    except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
        errors.append(str(exc))
    raise RuntimeError('No FX source available: ' + ' | '.join(errors))


def main():
    url = os.environ['SUPABASE_URL'].rstrip('/')
    key = os.environ['SUPABASE_SERVICE_ROLE_KEY']
    rate, provider_updated_at, provider = fetch_rate()
    now = datetime.now(timezone.utc)
    record = {'observed_date': now.date().isoformat(), 'collected_at': now.isoformat(),
              'provider_updated_at': provider_updated_at, 'usd_egp': rate, 'provider': provider}
    r = requests.post(url + '/rest/v1/usd_egp_history',
        headers={'apikey':key,'Authorization':f'Bearer {key}',
                 'Content-Type':'application/json', 'Prefer':'resolution=merge-duplicates,return=minimal'},
        params={'on_conflict':'observed_date'}, json=[record], timeout=30)
    if not r.ok:
        raise RuntimeError(f'Supabase HTTP {r.status_code}: {r.text[:800]}')
    print(f'Saved USD/EGP for {record["observed_date"]} from {provider} (rate {rate:.4f})')

if __name__ == '__main__':
    main()
