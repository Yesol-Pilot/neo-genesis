#!/usr/bin/env python3
"""Find the exact permission group ID for Registrar Write."""
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
        r = urllib.request.urlopen(req, timeout=30)
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
    dst_token = env['CF_API_TOKEN']  # has User scope (cfut_)

    # List all permission groups, filter for registrar-related
    code, data = call('GET', 'https://api.cloudflare.com/client/v4/user/tokens/permission_groups', dst_token)
    print(f'HTTP {code}, success={data.get("success") if isinstance(data, dict) else False}')

    if isinstance(data, dict) and data.get('result'):
        registrar_perms = []
        domain_perms = []
        for p in data['result']:
            name = p.get('name', '').lower()
            desc = p.get('description', '').lower()
            if 'registrar' in name or 'registrar' in desc:
                registrar_perms.append(p)
            elif 'domain' in name or 'domain' in desc:
                domain_perms.append(p)

        print()
        print('=== REGISTRAR-related permissions ===')
        for p in registrar_perms:
            print(f'  id: {p.get("id")}')
            print(f'    name:  {p.get("name")}')
            print(f'    desc:  {p.get("description")}')
            print(f'    scope: {p.get("scopes")}')
            print()

        print('=== DOMAIN-related permissions (top 10) ===')
        for p in domain_perms[:10]:
            print(f'  id: {p.get("id")}')
            print(f'    name:  {p.get("name")}')
            print(f'    desc:  {p.get("description")}')
            print(f'    scope: {p.get("scopes")}')
            print()

        # Also dump any with 'transfer' keyword
        print('=== TRANSFER-related permissions ===')
        for p in data['result']:
            n = p.get('name', '').lower()
            d = p.get('description', '').lower()
            if 'transfer' in n or 'transfer' in d:
                print(f'  {p.get("name"):40s} | {p.get("description", "")[:80]}')


if __name__ == '__main__':
    main()
