#!/usr/bin/env python3
"""Find CF Tunnel b2b699d6-... in which account + check Public Hostnames."""
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
TUNNEL = 'b2b699d6-142c-412c-b3eb-06d8e63e797c'

# Try both accounts
for acct_name, acct, token_key in [
    ('source/8f22c351', '8f22c351c93d878aacb918d9ee36a9c2', 'CF_API_TOKEN_NEOGENESIS'),
    ('target/b3fa19', 'b3fa19c512029d0e847f77ea4d9b1fa2', 'CF_API_TOKEN'),
]:
    token = env[token_key]
    print(f'\n=== {acct_name} ===')

    # Try tunnel GET
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/accounts/{acct}/cfd_tunnel/{TUNNEL}', token)
    print(f'  GET tunnel: HTTP {code}')
    if isinstance(data, dict):
        if data.get('success'):
            r = data.get('result', {})
            print(f'    name: {r.get("name")}')
            print(f'    status: {r.get("status")}')
            print(f'    created_at: {r.get("created_at")}')
            # List tunnel connections
            code2, d2 = call('GET', f'https://api.cloudflare.com/client/v4/accounts/{acct}/cfd_tunnel/{TUNNEL}/connections', token)
            print(f'    connections: HTTP {code2}, {len(d2.get("result", [])) if isinstance(d2, dict) else 0} active')
            # Configuration (Public Hostnames)
            code3, d3 = call('GET', f'https://api.cloudflare.com/client/v4/accounts/{acct}/cfd_tunnel/{TUNNEL}/configurations', token)
            print(f'    config: HTTP {code3}')
            if isinstance(d3, dict) and d3.get('result'):
                cfg = d3['result'].get('config', {})
                print(f'    ingress rules: {len(cfg.get("ingress", []))}')
                for i, rule in enumerate(cfg.get('ingress', [])):
                    print(f'       [{i}] hostname={rule.get("hostname"):30s} service={rule.get("service")}')
        else:
            errs = data.get('errors', [])
            for e in errs[:2]:
                print(f'    err[{e.get("code")}]: {e.get("message")[:60]}')
