#!/usr/bin/env python3
"""Diagnose where kott.kr registrar actually lives."""
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

    print('=' * 60)
    print('DIAGNOSIS: where does kott.kr registrar live?')
    print('=' * 60)

    # Check source account registrar list (full)
    print('\n[A] List source account registrar domains:')
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/accounts/{src_acct}/registrar/domains', src_token)
    print(f'  HTTP {code}')
    if isinstance(data, dict) and isinstance(data.get('result'), list):
        for d in data['result']:
            print(f'   - {d.get("name")}: pending_transfer={d.get("pending_transfer")} status={d.get("status")} current_registrar={d.get("current_registrar")}')

    # Check target account registrar list
    print('\n[B] List target account registrar domains:')
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/accounts/{dst_acct}/registrar/domains', dst_token)
    print(f'  HTTP {code}')
    if isinstance(data, dict) and isinstance(data.get('result'), list):
        for d in data['result']:
            print(f'   - {d.get("name")}: pending_transfer={d.get("pending_transfer")} status={d.get("status")} current_registrar={d.get("current_registrar")}')

    # Direct GET kott.kr from both
    print('\n[C] GET kott.kr from source registrar:')
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/accounts/{src_acct}/registrar/domains/kott.kr', src_token)
    print(f'  HTTP {code}')
    if isinstance(data, dict):
        if data.get('result'):
            r = data['result']
            print(f'  name: {r.get("name")}')
            print(f'  current_registrar: {r.get("current_registrar")}')
            print(f'  cloudflare_registration: {r.get("cloudflare_registration")}')
            print(f'  pending_transfer: {r.get("pending_transfer")}')
        else:
            print(f'  errors: {data.get("errors")}')

    print('\n[D] GET kott.kr from target registrar:')
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/accounts/{dst_acct}/registrar/domains/kott.kr', dst_token)
    print(f'  HTTP {code}')
    if isinstance(data, dict):
        if data.get('result'):
            r = data['result']
            print(f'  name: {r.get("name")}')
            print(f'  current_registrar: {r.get("current_registrar")}')
            print(f'  cloudflare_registration: {r.get("cloudflare_registration")}')
            print(f'  pending_transfer: {r.get("pending_transfer")}')
        else:
            print(f'  errors: {data.get("errors")}')

    # Check zone for kott.kr in both accounts
    print('\n[E] List zones in source account (search kott.kr):')
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones?name=kott.kr', src_token)
    print(f'  HTTP {code}')
    if isinstance(data, dict) and isinstance(data.get('result'), list):
        for z in data['result']:
            print(f'   - {z.get("name")}: account_id={z.get("account", {}).get("id")} status={z.get("status")}')

    print('\n[F] List zones in target account (search kott.kr):')
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones?name=kott.kr', dst_token)
    print(f'  HTTP {code}')
    if isinstance(data, dict) and isinstance(data.get('result'), list):
        for z in data['result']:
            print(f'   - {z.get("name")}: account_id={z.get("account", {}).get("id")} status={z.get("status")}')

    # Also recheck neogenesis.app state after the initiate
    print('\n[G] Re-check neogenesis.app state after initiate (should show pending_transfer=True):')
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/accounts/{src_acct}/registrar/domains/neogenesis.app', src_token)
    print(f'  HTTP {code}')
    if isinstance(data, dict) and data.get('result'):
        r = data['result']
        print(f'  pending_transfer: {r.get("pending_transfer")}')
        print(f'  domain_move: {r.get("domain_move")}')


if __name__ == '__main__':
    main()
