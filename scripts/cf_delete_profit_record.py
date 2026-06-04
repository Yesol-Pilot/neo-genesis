#!/usr/bin/env python3
"""Fix 2: Delete orphaned profit.neogenesis.app DNS CNAME record."""
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


apply = '--apply' in sys.argv
env = load_env()
token = env['CF_API_TOKEN']
NEW = 'f123426af0f297cd7704a5759d3ec938'

# Find profit record
code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones/{NEW}/dns_records?name=profit.neogenesis.app', token)
recs = data.get('result', []) if isinstance(data, dict) else []

if not recs:
    print('No profit.neogenesis.app record found.')
    sys.exit(0)

for r in recs:
    print(f'Found: {r["type"]:6s} {r["name"]:35s} -> {r["content"]} id={r["id"]}')
    if not apply:
        print(f'  [DRY-RUN] would DELETE /zones/{NEW}/dns_records/{r["id"]}')
        continue
    # Delete
    code, data = call('DELETE', f'https://api.cloudflare.com/client/v4/zones/{NEW}/dns_records/{r["id"]}', token)
    if isinstance(data, dict) and data.get('success'):
        print(f'  [OK] deleted')
    else:
        errs = data.get('errors', []) if isinstance(data, dict) else []
        msg = errs[0].get('message', '')[:80] if errs else 'unknown'
        print(f'  [FAIL] HTTP {code} | {msg}')

if not apply:
    print('\nRe-run with --apply to execute.')
