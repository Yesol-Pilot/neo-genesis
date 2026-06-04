#!/usr/bin/env python3
"""Quick post-activation check."""
import os, json, urllib.request, urllib.error, subprocess


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
dst_token = env['CF_API_TOKEN']
NEW_ZONE = 'f123426af0f297cd7704a5759d3ec938'

# Zone status
code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones/{NEW_ZONE}', dst_token)
z = data.get('result', {}) if isinstance(data, dict) else {}
print(f'Zone status: {z.get("status")}')
print(f'Activated on: {z.get("activated_on")}')
print(f'Nameservers: {z.get("name_servers")}')
print(f'Plan: {z.get("plan", {}).get("name")}')

# DNS records count
code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones/{NEW_ZONE}/dns_records?per_page=100', dst_token)
recs = data.get('result', []) if isinstance(data, dict) else []
print(f'\nDNS records in new zone: {len(recs)}')
for r in recs:
    print(f'  {r["type"]:6s} {r["name"]:40s} -> {r["content"][:55]}')

# Live DNS resolution using authoritative target NS
print('\n=== Live DNS resolution test ===')
test_domains = [
    'neogenesis.app',
    'ethica.neogenesis.app',
    'whylab.neogenesis.app',
    'aiforge.neogenesis.app',
    'dash.neogenesis.app',
]
for d in test_domains:
    try:
        r = subprocess.run(
            ['nslookup', d, '8.8.8.8'],
            capture_output=True, text=True, timeout=10,
        )
        out = r.stdout
        # Parse 'Address:' lines after the first (which is DNS server)
        lines = [l.strip() for l in out.split('\n') if l.strip()]
        addrs = []
        for i, ln in enumerate(lines):
            if ln.startswith('Name:') and d in ln:
                # next non-empty lines until we hit blank
                for follow in lines[i+1:i+5]:
                    if follow.startswith('Address') or follow.startswith('Addresses'):
                        addrs.append(follow.replace('Address:', '').replace('Addresses:', '').strip())
                break
        if addrs:
            print(f'  {d:40s} -> {addrs}')
        else:
            # Try canonical name
            cname_lines = [l for l in lines if 'canonical name' in l]
            if cname_lines:
                print(f'  {d:40s} -> {cname_lines[0]}')
            else:
                print(f'  {d:40s} -> (no A record)')
    except subprocess.TimeoutExpired:
        print(f'  {d:40s} -> TIMEOUT')
    except Exception as e:
        print(f'  {d:40s} -> ERR {e}')
