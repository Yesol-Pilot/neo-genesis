#!/usr/bin/env python3
"""Fix dash.neogenesis.app DNS: change to direct tunnel CNAME + proxied=True."""
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


def call(method, url, token, body=None):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, headers=headers, method=method, data=data)
    try:
        r = urllib.request.urlopen(req, timeout=20)
        return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8', errors='replace'))


apply = '--apply' in sys.argv
env = load_env()
token = env['CF_API_TOKEN']
NEW = 'f123426af0f297cd7704a5759d3ec938'
TUNNEL_ID = 'b2b699d6-142c-412c-b3eb-06d8e63e797c'

# Find dash record
code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones/{NEW}/dns_records?name=dash.neogenesis.app', token)
recs = data.get('result', []) if isinstance(data, dict) else []

if not recs:
    print('FAIL: dash record not found')
    sys.exit(1)

rec = recs[0]
print(f'Current: type={rec["type"]} content={rec["content"]} proxied={rec["proxied"]}')

new_body = {
    'type': 'CNAME',
    'name': 'dash.neogenesis.app',
    'content': f'{TUNNEL_ID}.cfargotunnel.com',
    'proxied': True,
    'ttl': 1,  # auto
    'comment': 'Neo Genesis Dashboard via CF Tunnel',
}
print(f'Desired: type=CNAME content={new_body["content"]} proxied=True')

if not apply:
    print('\n[DRY-RUN] Re-run with --apply')
    sys.exit(0)

# PUT (update)
code, data = call('PUT', f'https://api.cloudflare.com/client/v4/zones/{NEW}/dns_records/{rec["id"]}', token, new_body)
if isinstance(data, dict) and data.get('success'):
    r = data['result']
    print(f'\n[OK] Updated: content={r["content"]} proxied={r["proxied"]}')
else:
    errs = data.get('errors', []) if isinstance(data, dict) else []
    for e in errs[:3]:
        print(f'[FAIL] err[{e.get("code")}]: {e.get("message")}')
