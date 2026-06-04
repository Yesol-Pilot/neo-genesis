#!/usr/bin/env python3
"""Import 14 DNS records from backup into newly created target zone."""
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
        r = urllib.request.urlopen(req, timeout=30)
        return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body_text = e.read().decode('utf-8', errors='replace')
        try:
            return e.code, json.loads(body_text)
        except Exception:
            return e.code, {'raw': body_text}


def main():
    apply = '--apply' in sys.argv
    env = load_env()
    dst_token = env['CF_API_TOKEN']
    NEW_ZONE_ID = 'f123426af0f297cd7704a5759d3ec938'
    DOMAIN = 'neogenesis.app'

    backup_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        '.agent', 'knowledge', 'cf_zone_backup_20260514', 'zones_backup_pre_transfer.json',
    )
    with open(backup_path, encoding='utf-8') as f:
        backup = json.load(f)
    records = backup['zones'][DOMAIN]['dns_records']

    # First verify zone access
    print(f'[verify] GET zone {NEW_ZONE_ID}')
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones/{NEW_ZONE_ID}', dst_token)
    if code == 200 and isinstance(data, dict) and data.get('success'):
        z = data['result']
        print(f'  zone access OK: name={z.get("name")} status={z.get("status")}')
        print(f'  nameservers: {z.get("name_servers")}')
        print(f'  account: {z.get("account", {}).get("id")}')
    else:
        print(f'  HTTP {code} | {data.get("errors") if isinstance(data, dict) else data}')
        print(f'  ! Token scope does not include this zone. Owner needs to extend scope.')
        return 1

    # List existing records (newly created zone might have CF default records we need to skip/overwrite)
    print(f'\n[list existing records before import]')
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones/{NEW_ZONE_ID}/dns_records?per_page=100', dst_token)
    if isinstance(data, dict) and data.get('result'):
        existing = data['result']
        print(f'  existing records: {len(existing)}')
        for r in existing:
            print(f'   - {r["type"]:6s} {r["name"]:40s} {r["content"][:50]}')
    else:
        existing = []

    existing_keys = {(r['type'], r['name']): r['id'] for r in existing}

    if not apply:
        print(f'\n[DRY-RUN] Would import {len(records)} records (with conflict resolution)')
        for rec in records:
            key = (rec['type'], rec['name'])
            action = 'UPDATE' if key in existing_keys else 'CREATE'
            print(f'  {action:6s} {rec["type"]:6s} {rec["name"]:40s} {rec["content"][:50]}')
        return

    print(f'\n[import {len(records)} records]')
    ok = 0
    fail = 0
    for rec in records:
        key = (rec['type'], rec['name'])
        body = {
            'name': rec['name'],
            'type': rec['type'],
            'content': rec['content'],
            'proxied': rec['proxied'],
            'ttl': rec['ttl'],
        }
        if rec.get('comment'):
            body['comment'] = rec['comment']

        if key in existing_keys:
            existing_id = existing_keys[key]
            code, data = call(
                'PUT',
                f'https://api.cloudflare.com/client/v4/zones/{NEW_ZONE_ID}/dns_records/{existing_id}',
                dst_token,
                body,
            )
            verb = 'PUT'
        else:
            code, data = call(
                'POST',
                f'https://api.cloudflare.com/client/v4/zones/{NEW_ZONE_ID}/dns_records',
                dst_token,
                body,
            )
            verb = 'POST'

        if isinstance(data, dict) and data.get('success'):
            ok += 1
            print(f'  [OK]   {verb} {rec["type"]:6s} {rec["name"]}')
        else:
            fail += 1
            errs = data.get('errors', []) if isinstance(data, dict) else []
            msg = errs[0].get('message', '')[:80] if errs else 'unknown'
            print(f'  [FAIL] {verb} {rec["type"]:6s} {rec["name"]} | {msg}')

    print(f'\n[summary] {ok} OK / {fail} FAIL')

    # Re-list
    print('\n[verify final records]')
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones/{NEW_ZONE_ID}/dns_records?per_page=100', dst_token)
    if isinstance(data, dict) and data.get('result'):
        for r in data['result']:
            print(f'   - {r["type"]:6s} {r["name"]:40s} {r["content"][:50]:50s} proxied={r["proxied"]}')


if __name__ == '__main__':
    main()
