#!/usr/bin/env python3
"""CF Inter-Account Transfer initiate via API.

Pre-conditions:
  - source token (CF_API_TOKEN_NEOGENESIS) has "Cloudflare Registrar: Edit" perm
  - target token (CF_API_TOKEN) is verified active
  - both domains: transfer_conditions met, domain_move.ineligibility_reasons empty
  - pre-transfer backup completed (cf_zone_backup_20260514/)

This script initiates the transfer for both neogenesis.app + kott.kr.
After this runs, target account email will receive Accept requests (5-day window).
"""
import os
import json
import sys
import urllib.request
import urllib.error
from datetime import datetime


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


def preflight(token, src_acct, domain):
    """Check that domain is eligible before attempting move."""
    code, data = call(
        'GET',
        f'https://api.cloudflare.com/client/v4/accounts/{src_acct}/registrar/domains/{domain}',
        token,
    )
    if code != 200 or not data.get('success'):
        return False, f'GET failed: HTTP {code} {data}'
    r = data.get('result', {})
    if r.get('pending_transfer'):
        return False, 'already has pending_transfer'
    if r.get('transfer_frozen'):
        return False, f'transfer_frozen until {r.get("transfer_frozen_until")}'
    ineligibility = r.get('domain_move', {}).get('ineligibility_reasons', [])
    if ineligibility:
        return False, f'ineligibility_reasons: {ineligibility}'
    return True, 'eligible'


def initiate(token, src_acct, dst_acct, domain, dry_run=True):
    """PUT to initiate inter-account transfer."""
    url = f'https://api.cloudflare.com/client/v4/accounts/{src_acct}/registrar/domains/{domain}'
    body = {'domain_move': {'target_account_id': dst_acct}}

    if dry_run:
        print(f'  [DRY-RUN] would PUT {url}')
        print(f'  [DRY-RUN] body: {json.dumps(body)}')
        return True, 'dry-run'

    code, data = call('PUT', url, token, body)
    success = code in (200, 201) and isinstance(data, dict) and data.get('success')
    return success, {'http': code, 'response': data}


def main():
    dry_run = '--apply' not in sys.argv

    env = load_env()
    src_token = env['CF_API_TOKEN_NEOGENESIS']
    dst_acct = 'b3fa19c512029d0e847f77ea4d9b1fa2'
    src_acct = '8f22c351c93d878aacb918d9ee36a9c2'

    print('=' * 60)
    print('CF Inter-Account Transfer initiate')
    print(f'  src: {src_acct} (neogenesis.research)')
    print(f'  dst: {dst_acct} (dpthf1537)')
    print(f'  mode: {"DRY-RUN (use --apply to execute)" if dry_run else "LIVE EXECUTION"}')
    print('=' * 60)

    domains = ['neogenesis.app', 'kott.kr']
    log_entries = []

    for domain in domains:
        print()
        print(f'--- {domain} ---')

        ok, msg = preflight(src_token, src_acct, domain)
        print(f'  preflight: {"PASS" if ok else "FAIL"} | {msg}')
        if not ok:
            log_entries.append({'domain': domain, 'step': 'preflight', 'ok': False, 'msg': msg})
            continue

        ok, result = initiate(src_token, src_acct, dst_acct, domain, dry_run=dry_run)
        if dry_run:
            print(f'  initiate: dry-run OK')
        else:
            print(f'  initiate: {"SUCCESS" if ok else "FAIL"}')
            print(f'  detail: {json.dumps(result, indent=2)[:500]}')
            log_entries.append({'domain': domain, 'step': 'initiate', 'ok': ok, 'detail': result})

    # Save audit log
    if not dry_run:
        log_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            '.agent', 'shared-brain', 'web_action_log.jsonl',
        )
        entry = {
            'ts': datetime.now().isoformat() + '+09:00',
            'agent': 'claude-opus-4.7',
            'action': 'cf_inter_account_initiate',
            'src': src_acct,
            'dst': dst_acct,
            'domains': domains,
            'entries': log_entries,
        }
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
        print()
        print(f'[logged] {log_path}')

    print()
    print('=' * 60)
    if dry_run:
        print('DRY-RUN complete. Re-run with --apply to execute.')
    else:
        print('Done. Owner should check email for Accept requests within 5 days.')
    print('=' * 60)


if __name__ == '__main__':
    main()
