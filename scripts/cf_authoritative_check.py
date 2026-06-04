#!/usr/bin/env python3
"""Direct authoritative DNS query bypassing all caches."""
import subprocess
import urllib.request
import urllib.error
import time


def nslookup(domain, server='savanna.ns.cloudflare.com'):
    r = subprocess.run(['nslookup', domain, server], capture_output=True, text=True, timeout=10)
    return r.stdout


def http_test(url):
    """Force fresh HTTP test."""
    try:
        # Use Connection: close to avoid keep-alive caching
        req = urllib.request.Request(
            url, method='HEAD',
            headers={'User-Agent': 'test', 'Connection': 'close', 'Cache-Control': 'no-cache'}
        )
        r = urllib.request.urlopen(req, timeout=15)
        return r.status, dict(r.headers).get('Server', '?')[:20]
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers).get('Server', '?')[:20] if e.headers else '?'
    except Exception as e:
        return 0, str(e)[:60]


print('=== Authoritative query (savanna.ns.cloudflare.com) ===')
for d in ('profit.neogenesis.app', 'dash.neogenesis.app'):
    print(f'\n{d}:')
    out = nslookup(d)
    for ln in out.split('\n')[-8:]:
        if ln.strip():
            print(f'  | {ln}')

print('\n\n=== Fresh HTTP test (curl-like) ===')
for url in ('https://profit.neogenesis.app', 'https://dash.neogenesis.app'):
    status, server = http_test(url)
    print(f'  {url:40s} -> HTTP {status} server={server}')

print('\n=== Wait 20s and retest dash (tunnel config propagation) ===')
time.sleep(20)
for url in ('https://dash.neogenesis.app',):
    status, server = http_test(url)
    print(f'  {url:40s} -> HTTP {status} server={server}')
