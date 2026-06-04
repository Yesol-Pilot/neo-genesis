#!/usr/bin/env python3
"""Test target token (dpthf1537/b3fa19) against the same endpoint to compare permissions."""
import os
import json
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
    except Exception as e:
        return 0, {'error': str(e)}


def short(data):
    if not isinstance(data, dict):
        return str(data)[:80]
    if data.get('success'):
        return 'SUCCESS'
    errs = data.get('errors', [])
    if errs:
        return f'err[{errs[0].get("code")}]: {errs[0].get("message", "")[:80]}'
    return str(data)[:80]


def main():
    env = load_env()
    src_token = env['CF_API_TOKEN_NEOGENESIS']
    dst_token = env['CF_API_TOKEN']
    src_acct = '8f22c351c93d878aacb918d9ee36a9c2'
    dst_acct = 'b3fa19c512029d0e847f77ea4d9b1fa2'

    print('=' * 60)
    print('TEST 1: target token verify (cfut_ format supports verify)')
    print('=' * 60)
    code, data = call('GET', 'https://api.cloudflare.com/client/v4/user/tokens/verify', dst_token)
    print(f'HTTP {code} | {short(data)}')
    if isinstance(data, dict) and data.get('result'):
        print(json.dumps(data['result'], indent=2)[:500])

    print()
    print('=' * 60)
    print('TEST 2: source token verify (cfat_ may not support verify)')
    print('=' * 60)
    code, data = call('GET', 'https://api.cloudflare.com/client/v4/user/tokens/verify', src_token)
    print(f'HTTP {code} | {short(data)}')

    print()
    print('=' * 60)
    print('TEST 3: target token list registrar domains (target account)')
    print('=' * 60)
    code, data = call(
        'GET',
        f'https://api.cloudflare.com/client/v4/accounts/{dst_acct}/registrar/domains',
        dst_token,
    )
    print(f'HTTP {code} | success={data.get("success")} | count={len(data.get("result", [])) if isinstance(data, dict) else 0}')
    for d in (data.get('result', []) if isinstance(data.get('result'), list) else []):
        print(f'  - {d.get("name")}: pending_transfer={d.get("pending_transfer")} domain_move={d.get("domain_move")}')

    print()
    print('=' * 60)
    print('TEST 4: target token check inbound transfers (would receive request)')
    print('=' * 60)
    # try various paths for receiving side
    for path in (
        f'/accounts/{dst_acct}/registrar/transfers',
        f'/accounts/{dst_acct}/registrar/inter-account-transfers',
        f'/accounts/{dst_acct}/registrar/pending-transfers',
        f'/accounts/{dst_acct}/registrar/domain-moves',
    ):
        code, data = call('GET', f'https://api.cloudflare.com/client/v4{path}', dst_token)
        print(f'  HTTP {code} GET {path:60s} | {short(data)}')

    print()
    print('=' * 60)
    print('TEST 5: target token PUT on source domain (cross-account auth check)')
    print('=' * 60)
    url = f'https://api.cloudflare.com/client/v4/accounts/{src_acct}/registrar/domains/neogenesis.app/domain_move'
    code, data = call('PUT', url, dst_token, {'target_account_id': dst_acct})
    print(f'HTTP {code} | {short(data)}')


if __name__ == '__main__':
    main()
