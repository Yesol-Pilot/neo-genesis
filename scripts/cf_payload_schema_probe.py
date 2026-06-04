#!/usr/bin/env python3
"""Discover correct payload schema for inter-account transfer via PUT.
Now that perm is active, we can iterate without 403 noise.
"""
import os
import json
import urllib.request
import urllib.error
import time


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


def state(token, src_acct, domain):
    """Get current state for change tracking."""
    code, data = call('GET', f'https://api.cloudflare.com/client/v4/accounts/{src_acct}/registrar/domains/{domain}', token)
    r = data.get('result', {}) if isinstance(data, dict) else {}
    return {
        'pending_transfer': r.get('pending_transfer'),
        'domain_move': r.get('domain_move'),
        'transfer_conditions': r.get('transfer_conditions'),
    }


def short(data):
    if not isinstance(data, dict):
        return str(data)[:120]
    if data.get('success'):
        return f"SUCCESS msg={data.get('result', {}).get('message') or data.get('messages')}"
    errs = data.get('errors', [])
    if errs:
        return f"err[{errs[0].get('code')}]: {errs[0].get('message', '')[:80]}"
    return 'no errs'


def main():
    env = load_env()
    src_token = env['CF_API_TOKEN_NEOGENESIS']
    src_acct = '8f22c351c93d878aacb918d9ee36a9c2'
    dst_acct = 'b3fa19c512029d0e847f77ea4d9b1fa2'
    domain = 'neogenesis.app'
    url = f'https://api.cloudflare.com/client/v4/accounts/{src_acct}/registrar/domains/{domain}'

    print(f'BEFORE: {state(src_token, src_acct, domain)}\n')

    # Try various body shapes to trigger pending_transfer
    payloads = [
        ('1: domain_move.target_account_id', {'domain_move': {'target_account_id': dst_acct}}),
        ('2: domain_move.target_account', {'domain_move': {'target_account': dst_acct}}),
        ('3: domain_move.new_account_id', {'domain_move': {'new_account_id': dst_acct}}),
        ('4: domain_move.destination', {'domain_move': {'destination': dst_acct}}),
        ('5: domain_move.recipient', {'domain_move': {'recipient_account_id': dst_acct}}),
        ('6: domain_move.move_to', {'domain_move': {'move_to': dst_acct}}),
        ('7: domain_move with initiate flag', {'domain_move': {'target_account_id': dst_acct, 'initiate': True}}),
        ('8: domain_move with action=request', {'domain_move': {'target_account_id': dst_acct, 'action': 'request'}}),
        ('9: domain_move with action=initiate', {'domain_move': {'target_account_id': dst_acct, 'action': 'initiate'}}),
        ('10: top-level transfer_to', {'transfer_to': dst_acct}),
        ('11: top-level target_account_id', {'target_account_id': dst_acct}),
        ('12: top-level account_transfer', {'account_transfer': {'target_account_id': dst_acct}}),
        ('13: domain_move requested_account_id', {'domain_move': {'requested_account_id': dst_acct}}),
    ]

    for label, body in payloads:
        code, data = call('PUT', url, src_token, body)
        msg = short(data)
        st = state(src_token, src_acct, domain)
        triggered = st['pending_transfer']
        marker = '[TRIGGERED]' if triggered else '[no-effect]'
        print(f'{marker} {label:40s} HTTP {code} | {msg[:60]}')
        if triggered:
            print(f'           STATE NOW: {st}')
            print(f'           WINNING PAYLOAD: {json.dumps(body)}')
            return
        time.sleep(0.5)  # respect rate limits

    print()
    print('AFTER (no trigger): ', state(src_token, src_acct, domain))


if __name__ == '__main__':
    main()
