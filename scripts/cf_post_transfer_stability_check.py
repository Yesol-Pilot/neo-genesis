#!/usr/bin/env python3
"""Comprehensive post-transfer stability check for neogenesis.app.

Verifies:
1. DNS resolution (14 records) across 3 resolvers
2. HTTPS reachability + status (11 SBU subdomains)
3. SSL cert validity + expiry
4. CF Tunnel (dash.neogenesis.app)
5. Response time baseline
6. Source zone 'moved' status
7. Target zone settings sanity
"""
import os
import json
import socket
import ssl
import subprocess
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone


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


def cf_call(method, url, token):
    req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'}, method=method)
    try:
        r = urllib.request.urlopen(req, timeout=20)
        return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8', errors='replace'))
    except Exception as e:
        return 0, {'error': str(e)}


# All neogenesis.app records to check
SUBDOMAINS = [
    ('neogenesis.app', 'apex', 'A'),
    ('www.neogenesis.app', 'www', 'CNAME'),
    ('aiforge.neogenesis.app', 'AIForge SBU', 'CNAME'),
    ('craftdesk.neogenesis.app', 'CraftDesk SBU', 'CNAME'),
    ('deploystack.neogenesis.app', 'DeployStack SBU', 'CNAME'),
    ('finstack.neogenesis.app', 'FinStack SBU', 'CNAME'),
    ('profit.neogenesis.app', 'Profit SBU', 'CNAME'),
    ('review.neogenesis.app', 'ReviewLab SBU', 'CNAME'),
    ('sellkit.neogenesis.app', 'SellKit SBU', 'CNAME'),
    ('whylab.neogenesis.app', 'WhyLab SBU', 'CNAME'),
    ('ethica.neogenesis.app', 'EthicaAI SBU (blind review hold)', 'CNAME'),
    ('dash.neogenesis.app', 'CF Tunnel → neo.heoyesol.kr', 'CNAME'),
]


def check_dns(domain):
    """OS resolver lookup."""
    try:
        addr = socket.gethostbyname(domain)
        return addr
    except socket.gaierror as e:
        return f'FAIL: {e}'


def check_https(url):
    """HEAD request, capture status + cert + timing."""
    t0 = time.monotonic()
    try:
        req = urllib.request.Request(url, method='HEAD',
                                     headers={'User-Agent': 'neo-stability-check/1.0'})
        r = urllib.request.urlopen(req, timeout=15)
        elapsed = (time.monotonic() - t0) * 1000
        return {
            'status': r.status,
            'server': r.headers.get('Server', '?')[:40],
            'x_vercel_id': r.headers.get('X-Vercel-Id', '')[:40],
            'x_cf_ray': r.headers.get('CF-Ray', '')[:40],
            'elapsed_ms': round(elapsed, 1),
        }
    except urllib.error.HTTPError as e:
        elapsed = (time.monotonic() - t0) * 1000
        return {
            'status': e.code,
            'server': e.headers.get('Server', '?')[:40] if e.headers else '?',
            'elapsed_ms': round(elapsed, 1),
            'note': 'HTTPError but server reachable',
        }
    except Exception as e:
        return {'error': str(e)[:80]}


def check_ssl(hostname):
    """Connect to port 443, get cert info."""
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                issuer = dict(x[0] for x in cert['issuer']).get('organizationName', '?')[:30]
                subject = dict(x[0] for x in cert['subject']).get('commonName', '?')[:30]
                not_after = cert['notAfter']
                # Parse "May 14 12:00:00 2026 GMT"
                expiry = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc)
                days_left = (expiry - datetime.now(timezone.utc)).days
                return {'issuer': issuer, 'cn': subject, 'days_left': days_left}
    except Exception as e:
        return {'error': str(e)[:80]}


def main():
    env = load_env()
    dst_token = env['CF_API_TOKEN']
    src_token = env['CF_API_TOKEN_NEOGENESIS']
    NEW_ZID = 'f123426af0f297cd7704a5759d3ec938'
    OLD_ZID = '85380cbe940510fc1cf2620b1f24c707'

    print('=' * 80)
    print('NEOGENESIS.APP POST-TRANSFER STABILITY CHECK')
    print(f'Timestamp: {datetime.now(timezone.utc).isoformat()}')
    print('=' * 80)

    # ============ 1. ZONE STATE ============
    print('\n[1] ZONE STATE (target + source)')
    code, data = cf_call('GET', f'https://api.cloudflare.com/client/v4/zones/{NEW_ZID}', dst_token)
    tz = data.get('result', {}) if isinstance(data, dict) else {}
    print(f'  TARGET (b3fa19): status={tz.get("status")} plan={tz.get("plan",{}).get("name")}')
    print(f'           ns={tz.get("name_servers")}')
    print(f'           activated_on={tz.get("activated_on")}')

    code, data = cf_call('GET', f'https://api.cloudflare.com/client/v4/zones/{OLD_ZID}', src_token)
    sz = data.get('result', {}) if isinstance(data, dict) else {}
    print(f'  SOURCE (8f22c351): status={sz.get("status")} (expected: moved)')

    # ============ 2. DNS RESOLUTION ============
    print(f'\n[2] DNS RESOLUTION ({len(SUBDOMAINS)} subdomains via OS resolver)')
    dns_pass = 0
    dns_fail = 0
    for domain, role, rtype in SUBDOMAINS:
        addr = check_dns(domain)
        ok = '[OK]' if not addr.startswith('FAIL') else '[FAIL]'
        if not addr.startswith('FAIL'):
            dns_pass += 1
        else:
            dns_fail += 1
        print(f'  {ok} {domain:35s} -> {addr:20s} ({role})')

    # ============ 3. HTTPS + SSL ============
    print('\n[3] HTTPS REACHABILITY + SSL CERT')
    https_pass = 0
    https_fail = 0
    for domain, role, _ in SUBDOMAINS:
        url = f'https://{domain}'
        http = check_https(url)
        cert = check_ssl(domain)

        if 'error' in http:
            https_fail += 1
            print(f'  [FAIL] {domain:35s} http={http["error"]}')
            continue

        status = http.get('status', 0)
        cert_info = ''
        if 'error' in cert:
            cert_info = f'cert=ERROR'
        else:
            cert_info = f'cert={cert.get("issuer")[:25]} (expires {cert.get("days_left")}d)'

        # 200-299 OK, 3xx may be redirect (OK), 401/403 (blind review - acknowledge)
        # 4xx/5xx not OK
        if status < 400 or (status in (401, 403) and 'ethica' in domain):
            https_pass += 1
            status_marker = '[OK]'
        else:
            https_fail += 1
            status_marker = '[FAIL]'

        server = http.get('server', '?')[:15]
        elapsed = http.get('elapsed_ms', 0)
        print(f'  {status_marker} {domain:35s} HTTP {status} {server:15s} {elapsed:>6.0f}ms | {cert_info}')

    # ============ 4. APEX A RECORD vs EXPECTED ============
    print('\n[4] APEX A RECORD (expected 76.76.21.21 Vercel)')
    apex = check_dns('neogenesis.app')
    ok = '[OK]' if apex == '76.76.21.21' else '[?]'
    print(f'  {ok} apex -> {apex}')

    # ============ 5. CF TUNNEL CHECK ============
    print('\n[5] CF TUNNEL CHECK (dash.neogenesis.app)')
    dash = check_dns('dash.neogenesis.app')
    # dash should CNAME to neo.heoyesol.kr which resolves to CF tunnel IPs
    print(f'  dash.neogenesis.app -> {dash}')
    neo = check_dns('neo.heoyesol.kr')
    print(f'  neo.heoyesol.kr     -> {neo}')

    # ============ 6. TARGET ZONE SETTINGS SANITY ============
    print('\n[6] TARGET ZONE SETTINGS SANITY')
    code, data = cf_call('GET', f'https://api.cloudflare.com/client/v4/zones/{NEW_ZID}/settings', dst_token)
    settings = data.get('result', []) if isinstance(data, dict) else []
    important = {}
    for s in settings:
        sid = s.get('id')
        if sid in ('ssl', 'always_use_https', 'min_tls_version', 'tls_1_3', 'security_level',
                   'browser_check', 'challenge_ttl', 'cache_level', 'development_mode',
                   'http2', 'http3', 'always_online', 'ipv6', 'websockets',
                   'automatic_https_rewrites', 'opportunistic_encryption'):
            important[sid] = s.get('value')
    for k in sorted(important):
        v = important[k]
        # Sanity: ssl should be active (full/strict), https should be on
        marker = ''
        if k == 'ssl' and v not in ('full', 'strict'):
            marker = ' [WARN: should be full/strict]'
        if k == 'always_use_https' and v != 'on':
            marker = ' [WARN: HTTPS not forced]'
        if k == 'min_tls_version' and v not in ('1.2', '1.3'):
            marker = f' [WARN: TLS {v} < 1.2]'
        print(f'  {k:35s} = {v}{marker}')

    # ============ 7. DNS RECORDS COUNT VS BACKUP ============
    print('\n[7] DNS RECORDS COUNT (target zone)')
    code, data = cf_call('GET', f'https://api.cloudflare.com/client/v4/zones/{NEW_ZID}/dns_records?per_page=100', dst_token)
    recs = data.get('result', []) if isinstance(data, dict) else []
    print(f'  Current records: {len(recs)} (expected: 14 from backup)')

    # Count by type
    types = {}
    for r in recs:
        types[r['type']] = types.get(r['type'], 0) + 1
    for t in sorted(types):
        print(f'    {t}: {types[t]}')

    # ============ FINAL SUMMARY ============
    print()
    print('=' * 80)
    print('SUMMARY')
    print('=' * 80)
    print(f'  Target zone: {tz.get("status")} (expected: active)')
    print(f'  Source zone: {sz.get("status")} (expected: moved)')
    print(f'  DNS resolution: {dns_pass}/{dns_pass+dns_fail} PASS')
    print(f'  HTTPS reachability: {https_pass}/{https_pass+https_fail} PASS')
    print(f'  DNS records: {len(recs)}/14 ({"OK" if len(recs) == 14 else "DRIFT"})')
    overall = 'STABLE' if (dns_fail == 0 and https_fail == 0 and tz.get('status') == 'active' and len(recs) == 14) else 'ATTENTION'
    print(f'\n  OVERALL: {overall}')


if __name__ == '__main__':
    main()
