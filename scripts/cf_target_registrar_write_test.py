#!/usr/bin/env python3
"""Test if target token has Registrar Write perm by probing PUT/PATCH paths."""
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
    return 'no errs'


def main():
    env = load_env()
    dst_token = env['CF_API_TOKEN']
    src_token = env['CF_API_TOKEN_NEOGENESIS']
    dst_acct = 'b3fa19c512029d0e847f77ea4d9b1fa2'
    src_acct = '8f22c351c93d878aacb918d9ee36a9c2'

    # Test on target's own koreanllm.org — confirm target perm scope
    # If 403 = no Registrar Write
    # If 400 = endpoint exists, auth OK, just validation issue (= we have Write!)
    print('=' * 60)
    print('TEST: target token PUT on target-account domain (koreanllm.org)')
    print('Goal: distinguish 403 (no perm) vs 400 (perm OK, validation fail)')
    print('=' * 60)

    target_paths = [
        f'/accounts/{dst_acct}/registrar/domains/koreanllm.org/domain_move',
        f'/accounts/{dst_acct}/registrar/domains/koreanllm.org',
    ]

    for path in target_paths:
        url = f'https://api.cloudflare.com/client/v4{path}'
        # try PUT with empty body — should reveal whether write perm exists
        code, data = call('PUT', url, dst_token, {})
        print(f'  PUT {path[-60:]:60s}')
        print(f'    -> HTTP {code} | {short(data)}')

    print()
    print('=' * 60)
    print('TEST: same paths on source domain (neogenesis.app) for comparison')
    print('=' * 60)
    src_paths = [
        f'/accounts/{src_acct}/registrar/domains/neogenesis.app/domain_move',
        f'/accounts/{src_acct}/registrar/domains/neogenesis.app',
    ]
    for path in src_paths:
        url = f'https://api.cloudflare.com/client/v4{path}'
        code, data = call('PUT', url, src_token, {})
        print(f'  PUT {path[-60:]:60s}')
        print(f'    -> HTTP {code} (src token) | {short(data)}')

    print()
    print('=' * 60)
    print('GET /accounts/{dst}/registrar/domains/koreanllm.org full detail')
    print('=' * 60)
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/accounts/{dst_acct}/registrar/domains/koreanllm.org', dst_token)
    print(f'HTTP {code}')
    if isinstance(data, dict) and data.get('result'):
        r = data['result']
        print(f'  name: {r.get("name")}')
        print(f'  pending_transfer: {r.get("pending_transfer")}')
        print(f'  domain_move: {r.get("domain_move")}')
        # check available actions
        print(f'  permissions: {r.get("permissions")}')
        print(f'  available actions keys: {list(r.keys())}')


if __name__ == '__main__':
    main()
