#!/usr/bin/env python3
"""Check neo.heoyesol.kr DNS in heoyesol.kr zone."""
import os, json, urllib.request, urllib.error


def load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.local')
    env = {}
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line: continue
            k, v = line.split('=', 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def call(method, url, token):
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'}, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=20)
        return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8', errors='replace'))


env = load_env()
token = env['CF_API_TOKEN']
NEO_ZID = 'f123426af0f297cd7704a5759d3ec938'  # neogenesis.app

# Find heoyesol.kr zone id
code, data = call('GET', 'https://api.cloudflare.com/client/v4/zones?name=heoyesol.kr', token)
zones = data.get('result', []) if isinstance(data, dict) else []
print(f'heoyesol.kr zones found: {len(zones)}')
if not zones:
    print('FAIL: cannot find heoyesol.kr zone')
    exit(1)
HKR_ZID = zones[0]['id']
print(f'  zone id: {HKR_ZID}')
print(f'  account: {zones[0].get("account", {}).get("id")}')

# Get neo subdomain record
code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones/{HKR_ZID}/dns_records?name=neo.heoyesol.kr', token)
recs = data.get('result', []) if isinstance(data, dict) else []
print(f'\nneo.heoyesol.kr records:')
for r in recs:
    print(f'  type={r["type"]} content={r["content"]} proxied={r["proxied"]} comment={r.get("comment")}')

# Get dash subdomain in neogenesis.app
code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones/{NEO_ZID}/dns_records?name=dash.neogenesis.app', token)
recs = data.get('result', []) if isinstance(data, dict) else []
print(f'\ndash.neogenesis.app records (in NEW neogenesis.app zone):')
for r in recs:
    print(f'  type={r["type"]} content={r["content"]} proxied={r["proxied"]} comment={r.get("comment")}')
