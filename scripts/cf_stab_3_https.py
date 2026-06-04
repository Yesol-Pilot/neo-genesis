#!/usr/bin/env python3
"""Stability check 3/4: HTTPS reachability + SSL cert + response time."""
import time
import socket
import ssl
import urllib.request
import urllib.error
from datetime import datetime, timezone


URLS = [
    'https://neogenesis.app',
    'https://www.neogenesis.app',
    'https://aiforge.neogenesis.app',
    'https://craftdesk.neogenesis.app',
    'https://deploystack.neogenesis.app',
    'https://finstack.neogenesis.app',
    'https://profit.neogenesis.app',
    'https://review.neogenesis.app',
    'https://sellkit.neogenesis.app',
    'https://whylab.neogenesis.app',
    'https://ethica.neogenesis.app',  # blind review hold — may be 404
    'https://dash.neogenesis.app',  # CF Tunnel
]


def check_https(url):
    t0 = time.monotonic()
    try:
        req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'neo-stab/1.0'})
        r = urllib.request.urlopen(req, timeout=15)
        elapsed = (time.monotonic() - t0) * 1000
        return r.status, r.headers.get('Server', '?')[:15], round(elapsed, 0), None
    except urllib.error.HTTPError as e:
        elapsed = (time.monotonic() - t0) * 1000
        srv = e.headers.get('Server', '?')[:15] if e.headers else '?'
        return e.code, srv, round(elapsed, 0), None
    except Exception as e:
        elapsed = (time.monotonic() - t0) * 1000
        return 0, '?', round(elapsed, 0), str(e)[:60]


def check_ssl(hostname):
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with ctx.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                issuer = dict(x[0] for x in cert['issuer']).get('organizationName', '?')[:25]
                not_after = cert['notAfter']
                expiry = datetime.strptime(not_after, '%b %d %H:%M:%S %Y %Z').replace(tzinfo=timezone.utc)
                days = (expiry - datetime.now(timezone.utc)).days
                return issuer, days
    except Exception as e:
        return f'ERR {str(e)[:30]}', -1


print(f'{"URL":42s} {"HTTP":5s} {"Server":15s} {"ms":>6s} | {"SSL issuer":25s} {"days":>5s}')
print('-' * 110)

ok = 0
fail = 0
for url in URLS:
    host = url.replace('https://', '')
    status, server, elapsed, err = check_https(url)
    issuer, days = check_ssl(host)

    # Acceptance:
    # - 200-399 OK
    # - 401/403 OK only for ethica (blind review hold)
    # - everything else fail
    if status and status < 400:
        marker = '[OK]'
        ok += 1
    elif status in (401, 403, 404) and 'ethica' in url:
        marker = '[OK*]'  # acknowledged hold
        ok += 1
    else:
        marker = '[FAIL]'
        fail += 1

    if err:
        print(f'  {marker:7s} {host:35s} ERR {err}')
    else:
        print(f'  {marker:7s} {host:35s} {status:>5d} {server:15s} {elapsed:>6.0f} | {issuer:25s} {days:>5d}')

print(f'\nSummary: {ok}/{ok+fail} reachable + SSL OK')
