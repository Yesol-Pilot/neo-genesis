#!/usr/bin/env python3
"""CF Inter-Account Transfer API probe.
Goal: find if dashboard "Move Domain" button hits any callable endpoint.
"""
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
    data = None
    if body is not None:
        data = json.dumps(body).encode('utf-8')
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
    src_acct = '8f22c351c93d878aacb918d9ee36a9c2'
    dst_acct = 'b3fa19c512029d0e847f77ea4d9b1fa2'
    domain = 'neogenesis.app'

    print('=' * 60)
    print('STEP 1: list source registrar domains (base check)')
    print('=' * 60)
    code, data = call(
        'GET',
        f'https://api.cloudflare.com/client/v4/accounts/{src_acct}/registrar/domains',
        src_token,
    )
    print(f'HTTP {code}, success={data.get("success")}')
    if isinstance(data.get('result'), list):
        for d in data['result']:
            print(f'\n  domain: {d.get("name")}')
            print(f'    status: {d.get("status")}')
            xfer_keys = [k for k in d.keys() if any(t in k.lower() for t in ('transfer', 'move', 'account'))]
            for k in xfer_keys:
                print(f'    {k}: {d.get(k)}')

    print()
    print('=' * 60)
    print('STEP 2: probe candidate endpoint paths for inter-account transfer')
    print('=' * 60)

    # Endpoint paths the dashboard might use (educated guesses based on CF API patterns)
    # Key finding from STEP 1: domain has `domain_move: {ineligibility_reasons: []}` field
    # → strong hint that PATCH/PUT on domain or sub-resource works
    candidates = [
        # The domain_move sub-resource pattern (most likely)
        ('POST', f'/accounts/{src_acct}/registrar/domains/{domain}/domain_move', {'target_account_id': dst_acct}),
        ('PUT', f'/accounts/{src_acct}/registrar/domains/{domain}/domain_move', {'target_account_id': dst_acct}),
        ('PATCH', f'/accounts/{src_acct}/registrar/domains/{domain}/domain_move', {'target_account_id': dst_acct}),
        ('GET', f'/accounts/{src_acct}/registrar/domains/{domain}/domain_move', None),
        # PATCH on the domain itself with domain_move field
        ('PATCH', f'/accounts/{src_acct}/registrar/domains/{domain}', {'domain_move': {'target_account_id': dst_acct}}),
        ('PUT', f'/accounts/{src_acct}/registrar/domains/{domain}', {'domain_move': {'target_account_id': dst_acct}}),
        # Other guess patterns
        ('POST', f'/accounts/{src_acct}/registrar/domains/{domain}/account_transfer', {'target_account_id': dst_acct}),
        ('POST', f'/accounts/{src_acct}/registrar/domains/{domain}/move', {'target_account_id': dst_acct}),
        ('POST', f'/accounts/{src_acct}/registrar/domains/{domain}/inter-account-transfer', {'target_account_id': dst_acct}),
        ('GET', f'/accounts/{src_acct}/registrar/inter-account-transfers', None),
        ('GET', f'/accounts/{src_acct}/registrar/account_transfers', None),
        # snake_case + camelCase target field variants on the most likely endpoint
        ('POST', f'/accounts/{src_acct}/registrar/domains/{domain}/domain_move', {'targetAccountId': dst_acct}),
        ('POST', f'/accounts/{src_acct}/registrar/domains/{domain}/domain_move', {'target_account': dst_acct}),
        ('POST', f'/accounts/{src_acct}/registrar/domains/{domain}/domain_move', {'destination_account_id': dst_acct}),
    ]

    found_callable = []
    for method, path, body in candidates:
        url = f'https://api.cloudflare.com/client/v4{path}'
        code, data = call(method, url, src_token, body)
        msg = ''
        if isinstance(data, dict):
            if data.get('errors'):
                first = data['errors'][0] if data['errors'] else {}
                msg = f'err[{first.get("code")}]: {first.get("message", "")[:80]}'
            elif data.get('success'):
                msg = 'SUCCESS'
                found_callable.append((method, path))
        status_marker = '[OK]' if code in (200, 201) else ('[?]' if code in (400, 403, 409) else '[X]')
        print(f'{status_marker} HTTP {code} {method:5s} {path[:75]:75s} | {msg}')

    print()
    print('=' * 60)
    print('RESULT')
    print('=' * 60)
    if found_callable:
        print('CALLABLE endpoints found:')
        for m, p in found_callable:
            print(f'  {m} {p}')
    else:
        print('No callable inter-account transfer endpoint found.')
        print('All 404 = endpoint does not exist.')
        print('Some 4xx with hint = endpoint exists but params/auth wrong.')


if __name__ == '__main__':
    main()
