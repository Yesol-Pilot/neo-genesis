#!/usr/bin/env python3
"""Step 1+2: Create neogenesis.app zone in target account + import DNS records from backup.

Pre-condition: source dashboard "Move Domain" dialog is open, waiting for target to have the zone.
Post-condition: target account has neogenesis.app zone with 14 records, owner can complete Submit.
"""
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


def load_backup():
    backup_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        '.agent', 'knowledge', 'cf_zone_backup_20260514', 'zones_backup_pre_transfer.json',
    )
    with open(backup_path, encoding='utf-8') as f:
        return json.load(f)


def main():
    apply = '--apply' in sys.argv
    env = load_env()
    dst_token = env['CF_API_TOKEN']
    dst_acct = 'b3fa19c512029d0e847f77ea4d9b1fa2'
    domain = 'neogenesis.app'

    backup = load_backup()
    records = backup['zones'][domain]['dns_records']
    print(f'Backup loaded: {len(records)} records for {domain}')
    for r in records:
        print(f'  - {r["type"]:6s} {r["name"]:40s} {r["content"]:50s} proxied={r["proxied"]} ttl={r["ttl"]}')

    if not apply:
        print(f'\n[DRY-RUN] Re-run with --apply to:')
        print(f'  1. POST /zones (target: {dst_acct})  with name={domain}')
        print(f'  2. Import {len(records)} DNS records')
        return

    print()
    print(f'[1] Creating zone {domain} in target account {dst_acct}')
    code, data = call(
        'POST',
        'https://api.cloudflare.com/client/v4/zones',
        dst_token,
        {'name': domain, 'account': {'id': dst_acct}, 'type': 'full'},
    )
    print(f'  HTTP {code}')
    if isinstance(data, dict):
        if data.get('success'):
            new_zone_id = data['result']['id']
            print(f'  zone created: id={new_zone_id}')
            print(f'  new nameservers: {data["result"].get("name_servers")}')
        else:
            print(f'  errors: {json.dumps(data.get("errors"))}')
            errs = data.get('errors', [])
            if errs and 'already hosting' in str(errs).lower():
                print(f'  ! Zone already exists in another account — expected for transfer flow.')
                print(f'  ! CF requires source to release first. Check dashboard error.')
            return 1

    print()
    print(f'[2] Importing {len(records)} DNS records into new zone')
    success_count = 0
    fail_count = 0
    for rec in records:
        body = {
            'name': rec['name'],
            'type': rec['type'],
            'content': rec['content'],
            'proxied': rec['proxied'],
            'ttl': rec['ttl'],
        }
        if rec.get('comment'):
            body['comment'] = rec['comment']
        if rec.get('priority') is not None:
            body['priority'] = rec['priority']
        if rec.get('data'):
            body['data'] = rec['data']

        code, data = call(
            'POST',
            f'https://api.cloudflare.com/client/v4/zones/{new_zone_id}/dns_records',
            dst_token,
            body,
        )
        if isinstance(data, dict) and data.get('success'):
            success_count += 1
            print(f'  [OK] {rec["type"]:6s} {rec["name"]}')
        else:
            fail_count += 1
            errs = data.get('errors', []) if isinstance(data, dict) else []
            msg = errs[0].get('message', '')[:80] if errs else 'unknown'
            print(f'  [FAIL] {rec["type"]:6s} {rec["name"]} | {msg}')

    print()
    print(f'Imports: {success_count} OK / {fail_count} FAIL')
    print()
    print('Next step (owner):')
    print('  Source dashboard 의 Move Domain dialog 에서 Submit 클릭')
    print('  CF 가 이제 target 에 zone 있는 것 확인하고 transfer 수락함')


if __name__ == '__main__':
    main()
