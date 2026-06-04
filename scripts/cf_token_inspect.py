#!/usr/bin/env python3
"""Inspect CF token permissions to determine what scope is needed for inter-account transfer."""
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


def main():
    env = load_env()
    src_token = env['CF_API_TOKEN_NEOGENESIS']
    dst_token = env['CF_API_TOKEN']
    src_acct = '8f22c351c93d878aacb918d9ee36a9c2'
    dst_acct = 'b3fa19c512029d0e847f77ea4d9b1fa2'
    domain = 'neogenesis.app'

    print('=' * 60)
    print('Try PUT with various body shapes to find correct payload')
    print('=' * 60)

    payloads = [
        ('A: bare target_account_id', {'target_account_id': dst_acct}),
        ('B: bare target_account', {'target_account': dst_acct}),
        ('C: nested domain_move.target_account_id', {'domain_move': {'target_account_id': dst_acct}}),
        ('D: nested domain_move.target_account', {'domain_move': {'target_account': dst_acct}}),
        ('E: action=initiate + target', {'domain_move': {'action': 'initiate', 'target_account_id': dst_acct}}),
        ('F: snake start=true', {'domain_move': {'start': True, 'target_account_id': dst_acct}}),
        ('G: bare', {}),
    ]

    url = f'https://api.cloudflare.com/client/v4/accounts/{src_acct}/registrar/domains/{domain}/domain_move'

    for label, body in payloads:
        code, data = call('PUT', url, src_token, body)
        errs = data.get('errors', []) if isinstance(data, dict) else []
        first = errs[0] if errs else {}
        msg = first.get('message', '')[:100] if first else ('SUCCESS' if data.get('success') else json.dumps(data)[:100])
        err_code = first.get('code', '') if first else ''
        print(f'  HTTP {code} err[{err_code}] {label:50s} | {msg}')

    print()
    print('=' * 60)
    print('Same PUT on /registrar/domains/{domain} (no /domain_move)')
    print('=' * 60)
    url2 = f'https://api.cloudflare.com/client/v4/accounts/{src_acct}/registrar/domains/{domain}'

    for label, body in payloads:
        code, data = call('PUT', url2, src_token, body)
        errs = data.get('errors', []) if isinstance(data, dict) else []
        first = errs[0] if errs else {}
        msg = first.get('message', '')[:100] if first else ('SUCCESS' if data.get('success') else json.dumps(data)[:100])
        err_code = first.get('code', '') if first else ''
        print(f'  HTTP {code} err[{err_code}] {label:50s} | {msg}')

    print()
    print('=' * 60)
    print('Check Authorization header echo / error detail')
    print('=' * 60)
    # request with messages echo
    code, data = call('PUT', url, src_token, {'target_account_id': dst_acct})
    print(json.dumps(data, indent=2, ensure_ascii=False)[:1500])


if __name__ == '__main__':
    main()
