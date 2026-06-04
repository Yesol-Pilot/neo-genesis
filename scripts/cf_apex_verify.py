#!/usr/bin/env python3
"""Direct apex + HTTPS verification."""
import socket
import urllib.request
import urllib.error
import ssl


# 1. socket.gethostbyname (uses OS resolver)
print('=== socket.gethostbyname (OS resolver) ===')
for d in ('neogenesis.app', 'www.neogenesis.app', 'ethica.neogenesis.app', 'whylab.neogenesis.app', 'aiforge.neogenesis.app'):
    try:
        addr = socket.gethostbyname(d)
        print(f'  {d:40s} -> {addr}')
    except socket.gaierror as e:
        print(f'  {d:40s} -> FAIL {e}')

print()
print('=== HTTPS GET (verify cert + reach Vercel) ===')
for url in (
    'https://neogenesis.app',
    'https://aiforge.neogenesis.app',
    'https://ethica.neogenesis.app',
    'https://whylab.neogenesis.app',
):
    try:
        req = urllib.request.Request(url, method='HEAD')
        r = urllib.request.urlopen(req, timeout=15)
        status = r.status
        srv = r.headers.get('Server') or r.headers.get('x-vercel-id') or '?'
        print(f'  {url:45s} -> HTTP {status} server={srv[:40]}')
    except urllib.error.HTTPError as e:
        # 404 or other HTTP error is still a connection success
        print(f'  {url:45s} -> HTTP {e.code} (server reachable)')
    except urllib.error.URLError as e:
        print(f'  {url:45s} -> URLError {e.reason}')
    except Exception as e:
        print(f'  {url:45s} -> ERR {e}')

print()
print('=== Direct A query via authoritative NS (parsing-free) ===')
import subprocess
for d in ('neogenesis.app', 'www.neogenesis.app'):
    try:
        # Force A query, savanna NS
        r = subprocess.run(['nslookup', '-q=A', d, 'savanna.ns.cloudflare.com'],
                           capture_output=True, text=True, timeout=10)
        # Print raw last 6 lines
        for ln in r.stdout.strip().split('\n')[-8:]:
            print(f'  {d:30s} | {ln}')
        print()
    except Exception as e:
        print(f'  {d} -> ERR {e}')
