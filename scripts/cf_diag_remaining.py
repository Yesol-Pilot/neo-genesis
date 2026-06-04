#!/usr/bin/env python3
"""Diagnose: profit DNS state + tunnel connections + cache check."""
import os, json, urllib.request, urllib.error, socket, subprocess


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
NEW_ZID = 'f123426af0f297cd7704a5759d3ec938'
acct = 'b3fa19c512029d0e847f77ea4d9b1fa2'
TUNNEL = 'b2b699d6-142c-412c-b3eb-06d8e63e797c'

print('=== 1. profit.neogenesis.app DNS state ===')
code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones/{NEW_ZID}/dns_records?name=profit.neogenesis.app', token)
recs = data.get('result', []) if isinstance(data, dict) else []
print(f'  CF API records: {len(recs)} (expected: 0)')
for r in recs:
    print(f'   - {r["type"]:6s} {r["name"]:35s} -> {r["content"]}')

# Direct authoritative query
r = subprocess.run(['nslookup', 'profit.neogenesis.app', 'savanna.ns.cloudflare.com'], capture_output=True, text=True, timeout=10)
print(f'  Authoritative NS query (savanna.ns.cloudflare.com):')
for ln in r.stdout.strip().split('\n')[-6:]:
    print(f'   | {ln}')

print('\n=== 2. CF Tunnel connections + config version ===')
code, data = call('GET', f'https://api.cloudflare.com/client/v4/accounts/{acct}/cfd_tunnel/{TUNNEL}/connections', token)
conns = data.get('result', []) if isinstance(data, dict) else []
print(f'  Active connections: {len(conns)}')
for c in conns:
    print(f'   - id: {c.get("id")}')
    print(f'     opened: {c.get("opened_at")}')
    print(f'     origin_ip: {c.get("origin_ip")}')
    print(f'     client_id: {c.get("client_id")}')
    print(f'     client_version: {c.get("client_version")}')
    print(f'     conns: {len(c.get("conns", []))}')

print('\n=== 3. Current tunnel config ===')
code, data = call('GET', f'https://api.cloudflare.com/client/v4/accounts/{acct}/cfd_tunnel/{TUNNEL}/configurations', token)
if isinstance(data, dict) and data.get('result'):
    r = data['result']
    print(f'  version: {r.get("version")}')
    cfg = r.get('config', {})
    for i, rule in enumerate(cfg.get('ingress', [])):
        h = rule.get('hostname') or '(catch-all)'
        s = rule.get('service')
        print(f'   [{i}] {h:30s} -> {s}')

print('\n=== 4. Tunnel info + config source ===')
code, data = call('GET', f'https://api.cloudflare.com/client/v4/accounts/{acct}/cfd_tunnel/{TUNNEL}', token)
if isinstance(data, dict) and data.get('result'):
    r = data['result']
    print(f'  name: {r.get("name")}')
    print(f'  status: {r.get("status")}')
    print(f'  config_src: {r.get("config_src")}')  # 'cloudflare' = remote-managed, 'local' = local
    print(f'  remote_config: {r.get("remote_config")}')
