#!/usr/bin/env python3
"""Fix 3: Add dash.neogenesis.app to CF Tunnel ingress rules.

Tunnel: b2b699d6-142c-412c-b3eb-06d8e63e797c (neo-genesis, target account)
Goal: insert dash.neogenesis.app -> http://localhost:7700 BEFORE catch-all.
"""
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
acct = 'b3fa19c512029d0e847f77ea4d9b1fa2'
TUNNEL = 'b2b699d6-142c-412c-b3eb-06d8e63e797c'

# Get current config
print('[1] GET current tunnel config')
code, data = call('GET', f'https://api.cloudflare.com/client/v4/accounts/{acct}/cfd_tunnel/{TUNNEL}/configurations', token)
if not (isinstance(data, dict) and data.get('success')):
    print(f'  FAIL HTTP {code} | {data}')
    sys.exit(1)

cfg = data['result'].get('config', {})
ingress = cfg.get('ingress', [])
version = data['result'].get('version', 0)
print(f'  version: {version}')
print(f'  current ingress ({len(ingress)} rules):')
for i, r in enumerate(ingress):
    print(f'    [{i}] hostname={r.get("hostname") or "(catch-all)"} -> service={r.get("service")}')

# Build new ingress: insert dash.neogenesis.app BEFORE catch-all
new_ingress = []
for r in ingress:
    if not r.get('hostname'):  # catch-all
        # Insert dash before catch-all
        new_ingress.append({'hostname': 'dash.neogenesis.app', 'service': 'http://localhost:7700'})
    new_ingress.append(r)

# If no catch-all existed, add at end
if all(r.get('hostname') for r in new_ingress):
    new_ingress.append({'hostname': 'dash.neogenesis.app', 'service': 'http://localhost:7700'})
    new_ingress.append({'service': 'http_status:404'})

# Don't duplicate if already exists
hostnames = [r.get('hostname') for r in ingress]
if 'dash.neogenesis.app' in hostnames:
    print('\n  ! dash.neogenesis.app already in ingress. No-op.')
    sys.exit(0)

print(f'\n[2] NEW ingress ({len(new_ingress)} rules):')
for i, r in enumerate(new_ingress):
    print(f'    [{i}] hostname={r.get("hostname") or "(catch-all)"} -> service={r.get("service")}')

if not apply:
    print('\n[DRY-RUN] Re-run with --apply to execute.')
    sys.exit(0)

# PUT new config
print('\n[3] PUT updated config')
body = {'config': {'ingress': new_ingress}}
code, data = call(
    'PUT',
    f'https://api.cloudflare.com/client/v4/accounts/{acct}/cfd_tunnel/{TUNNEL}/configurations',
    token,
    body,
)
print(f'  HTTP {code}')
if isinstance(data, dict):
    if data.get('success'):
        new_v = data['result'].get('version')
        print(f'  SUCCESS new version: {new_v}')
    else:
        errs = data.get('errors', [])
        for e in errs[:3]:
            print(f'  err[{e.get("code")}]: {e.get("message")}')
        sys.exit(1)
