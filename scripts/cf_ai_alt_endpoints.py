#!/usr/bin/env python3
"""Probe alternative endpoint groups for AI features (Rules / Bots / Configuration)."""
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


def call(method, url, token, body=None):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, headers=headers, method=method, data=data)
    try:
        r = urllib.request.urlopen(req, timeout=20)
        return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8', errors='replace'))


env = load_env()
token = env['CF_API_TOKEN']
ZONE_ID = 'f123426af0f297cd7704a5759d3ec938'
ACCT_ID = 'b3fa19c512029d0e847f77ea4d9b1fa2'

print('=== AI Crawl Control endpoints ===')
for path in (
    f'/zones/{ZONE_ID}/bot_management',
    f'/zones/{ZONE_ID}/ai-crawl-control',
    f'/accounts/{ACCT_ID}/ai-crawl-control',
    f'/zones/{ZONE_ID}/ai-crawl-control/quick-actions',
):
    code, data = call('GET', f'https://api.cloudflare.com/client/v4{path}', token)
    msg = ''
    if isinstance(data, dict):
        if data.get('success'):
            msg = f'SUCCESS: {json.dumps(data.get("result"))[:100]}'
        else:
            errs = data.get('errors', [])
            msg = errs[0].get('message', '')[:80] if errs else 'no errs'
    print(f'  GET {path:60s} HTTP {code} | {msg}')

print('\n=== Old zone cleanup check (85380cbe...) ===')
src_token = env['CF_API_TOKEN_NEOGENESIS']
old_zid = '85380cbe940510fc1cf2620b1f24c707'
code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones/{old_zid}', src_token)
print(f'  GET /zones/{old_zid} HTTP {code}')
if isinstance(data, dict):
    if data.get('success'):
        z = data['result']
        print(f'  Status: {z.get("status")}')
        print(f'  Account: {z.get("account", {}).get("id")}')
    else:
        errs = data.get('errors', [])
        print(f'  Errors: {[e.get("message") for e in errs]}')

print('\n=== Source account 잔존 zones ===')
src_acct = '8f22c351c93d878aacb918d9ee36a9c2'
code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones?account.id={src_acct}', src_token)
zones = data.get('result', []) if isinstance(data, dict) else []
print(f'  count: {len(zones)}')
for z in zones:
    print(f'   - {z.get("name")}: id={z.get("id")} status={z.get("status")}')
