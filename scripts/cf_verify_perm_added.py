#!/usr/bin/env python3
"""Verify Registrar Edit permission added to source token.
Compare: 403 (no perm) vs 200/400 (perm exists, body validation).
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
    src_acct = '8f22c351c93d878aacb918d9ee36a9c2'

    # Probe with empty body — should NOT 403 anymore
    url = f'https://api.cloudflare.com/client/v4/accounts/{src_acct}/registrar/domains/neogenesis.app'
    code, data = call('PUT', url, src_token, {})

    print(f'PUT {url}')
    print(f'  HTTP {code}')
    if isinstance(data, dict):
        if data.get('success'):
            print(f'  result: SUCCESS (no-op PUT) - permission VERIFIED')
            return 0
        errs = data.get('errors', [])
        if errs:
            first = errs[0]
            err_code = first.get('code')
            err_msg = first.get('message', '')
            print(f'  err[{err_code}]: {err_msg}')
            if err_code == 10000 and 'Authentication' in err_msg:
                print()
                print('STATUS: 403 Authentication error - permission NOT added yet')
                print('Owner needs to verify the perm was saved in the token.')
                return 1
            else:
                # Non-auth error — perm IS added, just validation noise
                print()
                print('STATUS: Permission added (non-auth error). Safe to proceed with --apply.')
                return 0
    return 1


if __name__ == '__main__':
    import sys
    sys.exit(main())
