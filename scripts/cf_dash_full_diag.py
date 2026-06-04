#!/usr/bin/env python3
"""Full diag: dash.neogenesis.app HTTPS + check neo.heoyesol.kr direct."""
import urllib.request
import urllib.error
import socket
import subprocess


def http_head(url):
    try:
        req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'diag/1.0'})
        r = urllib.request.urlopen(req, timeout=15)
        return r.status, dict(r.headers).get('Server'), dict(r.headers).get('Cf-Ray', '')
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers).get('Server') if e.headers else '?', dict(e.headers).get('Cf-Ray', '') if e.headers else ''
    except Exception as e:
        return 0, str(e)[:50], ''


print('=== HTTPS test ===')
for url in ('https://neo.heoyesol.kr', 'https://dash.neogenesis.app'):
    s, srv, ray = http_head(url)
    print(f'  {url:35s} HTTP {s} server={srv} cf-ray={ray}')

print('\n=== DNS chain ===')
# Use dig-like approach via subprocess
for d in ('neo.heoyesol.kr', 'dash.neogenesis.app'):
    print(f'\n{d}:')
    r = subprocess.run(['nslookup', '-debug', d, '1.1.1.1'], capture_output=True, text=True, timeout=10)
    out = r.stdout
    for ln in out.split('\n'):
        if 'canonical name' in ln or 'CNAME' in ln or 'address' in ln.lower():
            print(f'  | {ln.strip()}')

# Also direct socket check
print('\n=== Socket gethostbyname ===')
for d in ('neo.heoyesol.kr', 'dash.neogenesis.app', 'b2b699d6-142c-412c-b3eb-06d8e63e797c.cfargotunnel.com'):
    try:
        addr = socket.gethostbyname(d)
        print(f'  {d:60s} -> {addr}')
    except socket.gaierror as e:
        print(f'  {d:60s} -> FAIL {e}')
