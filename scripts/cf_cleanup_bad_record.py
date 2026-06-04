#!/usr/bin/env python3
"""Delete accidentally created dash.neogenesis.app.heoyesol.kr CNAME."""
import os, json, sys, urllib.request, urllib.error


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
HKR_ZID = '4e032e6aef90985fd2d613753be75745'  # heoyesol.kr

# Find the accidental record
code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones/{HKR_ZID}/dns_records?name=dash.neogenesis.app.heoyesol.kr', token)
recs = data.get('result', []) if isinstance(data, dict) else []
print(f'Found {len(recs)} records')

apply = '--apply' in sys.argv
for r in recs:
    print(f'  {r["type"]:6s} {r["name"]:50s} -> {r["content"]}')
    if apply:
        code, data = call('DELETE', f'https://api.cloudflare.com/client/v4/zones/{HKR_ZID}/dns_records/{r["id"]}', token)
        ok = data.get('success') if isinstance(data, dict) else False
        print(f'    {"[OK] deleted" if ok else f"[FAIL] {data}"}')

if not apply:
    print('\n[DRY-RUN] Re-run with --apply')
