#!/usr/bin/env python3
"""Check target account for inbound transfer requests."""
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
        body_text = e.read().decode('utf-8', errors='replace')
        try:
            return e.code, json.loads(body_text)
        except Exception:
            return e.code, {'raw': body_text}


def main():
    env = load_env()
    dst_token = env['CF_API_TOKEN']
    src_token = env['CF_API_TOKEN_NEOGENESIS']
    dst_acct = 'b3fa19c512029d0e847f77ea4d9b1fa2'
    src_acct = '8f22c351c93d878aacb918d9ee36a9c2'

    # Target account: list all registrar domains again
    print('[1] Target registrar domains (NOW):')
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/accounts/{dst_acct}/registrar/domains', dst_token)
    print(f'   HTTP {code}')
    for d in data.get('result', []):
        print(f'   - {d.get("name")}: pending_transfer={d.get("pending_transfer")} status={d.get("status")}')

    # Direct GET on neogenesis.app from target to see if it now appears as pending
    print('\n[2] GET neogenesis.app from TARGET account:')
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/accounts/{dst_acct}/registrar/domains/neogenesis.app', dst_token)
    print(f'   HTTP {code}')
    if isinstance(data, dict):
        r = data.get('result', {}) or {}
        print(f'   pending_transfer: {r.get("pending_transfer")}')
        print(f'   domain_move: {r.get("domain_move")}')
        print(f'   actionable_metadata: {r.get("actionable_metadata")}')
        print(f'   permissions: {r.get("permissions")}')
        if data.get('errors'):
            print(f'   errors: {data["errors"]}')

    # Check for /transfer_in or pending receive
    print('\n[3] Various pending-action endpoints in target:')
    paths = [
        f'/accounts/{dst_acct}/registrar/domains/transfer_in',
        f'/accounts/{dst_acct}/registrar/transfer_in',
        f'/accounts/{dst_acct}/registrar/actions',
        f'/accounts/{dst_acct}/registrar/actionable_metadata',
        f'/accounts/{dst_acct}/registrar/pending_actions',
        f'/accounts/{dst_acct}/registrar/domains/neogenesis.app/transfer_in',
        f'/accounts/{dst_acct}/registrar/domains/neogenesis.app/domain_move',
        f'/accounts/{dst_acct}/registrar/domains/neogenesis.app/actionable_metadata',
    ]
    for p in paths:
        code, data = call('GET', f'https://api.cloudflare.com/client/v4{p}', dst_token)
        msg = ''
        if isinstance(data, dict):
            if data.get('success'):
                msg = f'SUCCESS: {json.dumps(data.get("result"))[:80]}'
            elif data.get('errors'):
                msg = f'err: {data["errors"][0].get("message", "")[:60]}'
        print(f'   HTTP {code} GET {p[-50:]:50s} | {msg}')


if __name__ == '__main__':
    main()
