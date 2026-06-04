#!/usr/bin/env python3
"""Check kott.kr zone state in source + DNS records for move planning."""
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
src_token = env['CF_API_TOKEN_NEOGENESIS']
src_acct = '8f22c351c93d878aacb918d9ee36a9c2'

# Find kott.kr zone in source
code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones?name=kott.kr', src_token)
zones = data.get('result', []) if isinstance(data, dict) else []
print(f'Zones named kott.kr in source: {len(zones)}')
for z in zones:
    print(f'  id: {z.get("id")}')
    print(f'  name: {z.get("name")}')
    print(f'  status: {z.get("status")}')
    print(f'  account: {z.get("account", {}).get("id")}')
    print(f'  name_servers: {z.get("name_servers")}')
    print(f'  original_name_servers: {z.get("original_name_servers")}')
    print(f'  original_registrar: {z.get("original_registrar")}')
    print(f'  modified_on: {z.get("modified_on")}')
    zid = z.get('id')
    # Records
    code2, data2 = call('GET', f'https://api.cloudflare.com/client/v4/zones/{zid}/dns_records?per_page=100', src_token)
    recs = data2.get('result', []) if isinstance(data2, dict) else []
    print(f'  records ({len(recs)}):')
    for r in recs:
        print(f'    {r["type"]:6s} {r["name"]:30s} -> {r["content"][:50]} proxied={r["proxied"]} ttl={r["ttl"]}')
