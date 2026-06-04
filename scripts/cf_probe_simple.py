#!/usr/bin/env python3
"""Single-PUT probe: try one schema variant + check state."""
import os
import json
import sys
import urllib.request
import urllib.error


def load_env():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env.local')
    env = {}
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
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
        body_text = e.read().decode('utf-8', errors='replace')
        try:
            return e.code, json.loads(body_text)
        except Exception:
            return e.code, {'raw': body_text}


def main():
    env = load_env()
    src_token = env['CF_API_TOKEN_NEOGENESIS']
    src_acct = '8f22c351c93d878aacb918d9ee36a9c2'
    dst_acct = 'b3fa19c512029d0e847f77ea4d9b1fa2'
    dom = 'neogenesis.app'

    # First, get FULL current state
    url_get = f'https://api.cloudflare.com/client/v4/accounts/{src_acct}/registrar/domains/{dom}'
    code, data = call('GET', url_get, src_token)
    r = data.get('result', {}) if isinstance(data, dict) else {}
    print('=== FULL state keys ===')
    for k, v in r.items():
        if k in ('domain_move', 'transfer_conditions', 'permissions', 'policies', 'transfer_in', 'pending_transfer', 'status', 'last_known_status', 'cor_locked', 'material_changes'):
            print(f'  {k}: {v}')

    # Check what relations/policies say
    print('\n  relations:', r.get('relations'))
    print('  cloudflare_registration:', r.get('cloudflare_registration'))

    # The actionable_metadata field might hint at available actions
    print('\n  actionable_metadata:', r.get('actionable_metadata'))


if __name__ == '__main__':
    main()
