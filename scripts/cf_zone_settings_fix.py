#!/usr/bin/env python3
"""Fix 1: Apply zone settings always_use_https=on + min_tls_version=1.2."""
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

fixes = [
    ('always_use_https', 'on', 'Force HTTP -> HTTPS redirect'),
    ('min_tls_version', '1.2', 'Block TLS 1.0/1.1'),
]

for sid, val, note in fixes:
    url = f'https://api.cloudflare.com/client/v4/zones/{NEW}/settings/{sid}'
    print(f'\n[{sid}] target = "{val}" ({note})')
    if not apply:
        print(f'  [DRY-RUN] would PATCH with {{"value": "{val}"}}')
        continue
    code, data = call('PATCH', url, token, {'value': val})
    if isinstance(data, dict) and data.get('success'):
        result = data.get('result', {})
        print(f'  [OK] HTTP {code} | new value: {result.get("value")}')
    else:
        errs = data.get('errors', []) if isinstance(data, dict) else []
        msg = errs[0].get('message', '')[:80] if errs else 'unknown'
        print(f'  [FAIL] HTTP {code} | {msg}')

if not apply:
    print('\nRe-run with --apply to execute.')
