#!/usr/bin/env python3
"""Stability check 1/4: Zone state + DNS records count."""
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
dst = env['CF_API_TOKEN']
src = env['CF_API_TOKEN_NEOGENESIS']
NEW = 'f123426af0f297cd7704a5759d3ec938'
OLD = '85380cbe940510fc1cf2620b1f24c707'

print('[1.1] TARGET zone')
code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones/{NEW}', dst)
z = data.get('result', {})
print(f'  status={z.get("status")}  plan={z.get("plan",{}).get("name")}  activated={z.get("activated_on")}')
print(f'  ns={z.get("name_servers")}')

print('\n[1.2] SOURCE zone (should be moved)')
code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones/{OLD}', src)
z = data.get('result', {})
print(f'  status={z.get("status")}  ns={z.get("name_servers")}')

print('\n[1.3] DNS records count (target)')
code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones/{NEW}/dns_records?per_page=100', dst)
recs = data.get('result', [])
types = {}
for r in recs:
    types[r['type']] = types.get(r['type'], 0) + 1
print(f'  total: {len(recs)} (expected 14)')
for t in sorted(types):
    print(f'    {t}: {types[t]}')
