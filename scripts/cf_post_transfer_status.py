#!/usr/bin/env python3
"""Verify post-transfer state: source should be empty, target should own neogenesis.app."""
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
    src_token = env['CF_API_TOKEN_NEOGENESIS']
    dst_token = env['CF_API_TOKEN']
    src_acct = '8f22c351c93d878aacb918d9ee36a9c2'
    dst_acct = 'b3fa19c512029d0e847f77ea4d9b1fa2'

    print('[1] Source account registrar (should be EMPTY now):')
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/accounts/{src_acct}/registrar/domains', src_token)
    print(f'   HTTP {code} count={len(data.get("result", []))}')
    for d in data.get('result', []):
        print(f'   - {d.get("name")}: current_registrar={d.get("current_registrar")} status={d.get("status")} pending={d.get("pending_transfer")}')

    print('\n[2] Target account registrar (should have neogenesis.app):')
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/accounts/{dst_acct}/registrar/domains', dst_token)
    print(f'   HTTP {code} count={len(data.get("result", []))}')
    for d in data.get('result', []):
        print(f'   - {d.get("name")}: current_registrar={d.get("current_registrar")} status={d.get("status")} pending={d.get("pending_transfer")} expires={d.get("expires_at")}')

    print('\n[3] Source zones (does source zone still exist?):')
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones?account.id={src_acct}', src_token)
    print(f'   HTTP {code} count={len(data.get("result", []))}')
    for z in data.get('result', []):
        print(f'   - {z.get("name")}: status={z.get("status")} ns={z.get("name_servers")}')

    print('\n[4] Target zones:')
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones?account.id={dst_acct}', dst_token)
    print(f'   HTTP {code} count={len(data.get("result", []))}')
    for z in data.get('result', []):
        print(f'   - {z.get("name")}: status={z.get("status")} ns={z.get("name_servers")}')

    print('\n[5] DNS resolution check (live):')
    import subprocess
    for d in ('neogenesis.app', 'ethica.neogenesis.app', 'whylab.neogenesis.app'):
        try:
            r = subprocess.run(['nslookup', '-type=A', d, '8.8.8.8'], capture_output=True, text=True, timeout=10)
            out = r.stdout
            # Find Address line after Name line
            lines = out.split('\n')
            for i, ln in enumerate(lines):
                if d in ln.lower() and 'Name:' in ln:
                    if i+1 < len(lines):
                        print(f'   {d:35s} -> {lines[i+1].strip()}')
                    break
            else:
                addr_lines = [l.strip() for l in lines if l.startswith('Address') and '#' not in l]
                if addr_lines:
                    print(f'   {d:35s} -> {addr_lines[-1]}')
                else:
                    print(f'   {d:35s} -> (no result)')
        except Exception as e:
            print(f'   {d:35s} -> ERROR {e}')


if __name__ == '__main__':
    main()
