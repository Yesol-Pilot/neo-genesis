#!/usr/bin/env python3
"""Stability check 4/4: Target zone settings sanity."""
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
NEW = 'f123426af0f297cd7704a5759d3ec938'

code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones/{NEW}/settings', dst)
settings = data.get('result', [])
crit = {s['id']: s.get('value') for s in settings}

# Sanity check critical settings
print('=== CRITICAL ZONE SETTINGS ===')

checks = [
    ('ssl', 'flexible|full|strict', 'SSL mode'),
    ('always_use_https', 'on', 'Force HTTPS redirect'),
    ('min_tls_version', '1.2|1.3', 'Min TLS version'),
    ('tls_1_3', 'on|zrt', 'TLS 1.3 enabled'),
    ('automatic_https_rewrites', 'on', 'Auto HTTPS rewrites'),
    ('http2', 'on', 'HTTP/2 enabled'),
    ('http3', 'on', 'HTTP/3 enabled'),
    ('ipv6', 'on', 'IPv6 enabled'),
    ('security_level', 'low|medium|high|essentially_off', 'Security level'),
    ('browser_check', 'on', 'Browser integrity check'),
    ('opportunistic_encryption', 'on', 'Opportunistic encryption'),
    ('websockets', 'on', 'WebSockets'),
    ('always_online', 'on|off', 'Always Online'),
    ('development_mode', 'off', 'Dev mode (should be OFF)'),
    ('cache_level', 'aggressive|basic|simplified', 'Cache level'),
    ('challenge_ttl', '*', 'Challenge TTL'),
]

warn_count = 0
ok_count = 0
for sid, expected, label in checks:
    actual = crit.get(sid, '(missing)')
    actual_str = str(actual) if not isinstance(actual, dict) else json.dumps(actual)[:50]

    if expected == '*':
        marker = '[--]'
    elif '|' in expected:
        allowed = expected.split('|')
        if str(actual) in allowed:
            marker = '[OK]'
            ok_count += 1
        else:
            marker = '[WARN]'
            warn_count += 1
    else:
        if str(actual) == expected:
            marker = '[OK]'
            ok_count += 1
        else:
            marker = '[WARN]'
            warn_count += 1

    print(f'  {marker:7s} {sid:30s} = {actual_str:25s} | {label}')

print(f'\nSettings: {ok_count} OK / {warn_count} WARN (expected on Free Tier)')

# Also check DNSSEC
print('\n=== DNSSEC ===')
code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones/{NEW}/dnssec', dst)
if isinstance(data, dict) and data.get('result'):
    r = data['result']
    print(f'  Status: {r.get("status")}')
    print(f'  Modified: {r.get("modified_on")}')
elif isinstance(data, dict):
    errs = data.get('errors', [])
    if errs:
        print(f'  err: {errs[0].get("message")}')
