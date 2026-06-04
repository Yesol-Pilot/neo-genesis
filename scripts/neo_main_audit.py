#!/usr/bin/env python3
"""Audit neogenesis.app main hub site (NOT subsidiaries)."""
import urllib.request
import urllib.error
import json
import re
import time
from xml.etree import ElementTree as ET


def fetch(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'neo-main-audit/1.0'})
        r = urllib.request.urlopen(req, timeout=timeout)
        return r.status, r.read().decode('utf-8', errors='replace'), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, '', dict(e.headers) if e.headers else {}
    except Exception as e:
        return 0, str(e), {}


BASE = 'https://neogenesis.app'

print('=== [1] HOMEPAGE ===')
t0 = time.monotonic()
status, html, headers = fetch(BASE)
elapsed = (time.monotonic() - t0) * 1000
print(f'  HTTP {status} {elapsed:.0f}ms  server={headers.get("server")}')
print(f'  size={len(html):,} chars  age={headers.get("age")}')

# Count Schema blocks
schema_blocks = re.findall(r'application/ld\+json["\']?\s*>(.*?)</script>', html, re.DOTALL)
schema_types = []
for b in schema_blocks:
    try:
        d = json.loads(b)
        t = d.get('@type')
        if isinstance(t, list):
            schema_types.extend(t)
        elif t:
            schema_types.append(t)
        # nested @graph
        for g in d.get('@graph', []):
            gt = g.get('@type')
            if gt:
                schema_types.append(gt if isinstance(gt, str) else gt[0])
    except Exception:
        pass

print(f'  Schema.org blocks: {len(schema_blocks)}')
print(f'  Schema @types: {set(schema_types)}')

# Visible canonical URL strings
canonical_mentions = len(re.findall(r'neogenesis\.app', html))
print(f'  "neogenesis.app" mentions (HTML): {canonical_mentions}')

print('\n=== [2] SITEMAP ===')
status, sitemap_xml, _ = fetch(f'{BASE}/sitemap.xml')
print(f'  HTTP {status}  size={len(sitemap_xml):,}')
try:
    root = ET.fromstring(sitemap_xml)
    urls = [loc.text for loc in root.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
    print(f'  URLs in sitemap: {len(urls)}')

    # Categorize
    categories = {'blog': 0, 'data/research': 0, 'sbu': 0, 'docs': 0, 'faq': 0, 'cite': 0, 'home': 0, 'press': 0, 'other': 0}
    for u in urls:
        path = u.replace(BASE, '').replace('https://neogenesis.app', '')
        if path.startswith('/blog'):
            categories['blog'] += 1
        elif path.startswith('/data/research'):
            categories['data/research'] += 1
        elif path.startswith('/sbu'):
            categories['sbu'] += 1
        elif path.startswith('/docs'):
            categories['docs'] += 1
        elif path.startswith('/faq'):
            categories['faq'] += 1
        elif path.startswith('/cite'):
            categories['cite'] += 1
        elif path.startswith('/press'):
            categories['press'] += 1
        elif path == '/' or not path:
            categories['home'] += 1
        else:
            categories['other'] += 1
    for k, v in categories.items():
        if v:
            print(f'    {k:20s}: {v}')
except Exception as e:
    print(f'  PARSE ERROR: {e}')

print('\n=== [3] CORE PAGES PROBE ===')
core_pages = [
    '/',
    '/cite',
    '/faq',
    '/about',
    '/data',
    '/blog',
    '/llms.txt',
    '/llms-full.txt',
    '/robots.txt',
    '/sbu/whylab',
    '/sbu/ethicaai',
    '/docs/architecture',
]
for path in core_pages:
    t0 = time.monotonic()
    status, body, h = fetch(f'{BASE}{path}')
    elapsed = (time.monotonic() - t0) * 1000
    size = len(body) if body else 0
    print(f'  {path:30s} HTTP {status:>3d} {elapsed:>5.0f}ms {size:>8,} chars')

print('\n=== [4] llms-full.txt ANALYSIS ===')
status, llms, _ = fetch(f'{BASE}/llms-full.txt')
print(f'  size: {len(llms):,} chars')
print(f'  lines: {llms.count(chr(10)):,}')
# Section count
sections = re.findall(r'^##? ', llms, re.MULTILINE)
print(f'  H1/H2 sections: {len(sections)}')
# FACTs / structured data signals
facts = re.findall(r'^FACT-\d+', llms, re.MULTILINE)
print(f'  FACT-N entries: {len(facts)}')
bibtex = llms.count('@inproceedings') + llms.count('@article') + llms.count('@misc')
print(f'  BibTeX entries: {bibtex}')
hf_datasets = len(re.findall(r'huggingface\.co/datasets/neogenesislab/', llms))
print(f'  HF dataset refs: {hf_datasets}')
wikidata_q = re.findall(r'Q\d{6,9}', llms)
print(f'  Wikidata Q-IDs: {len(set(wikidata_q))} unique')

print('\n=== [5] AI/SEO META ===')
status, robots, _ = fetch(f'{BASE}/robots.txt')
ai_bot_blocked = []
ai_bot_allowed = []
known_ai_bots = ['GPTBot', 'ChatGPT-User', 'ClaudeBot', 'CCBot', 'PerplexityBot', 'Google-Extended', 'anthropic-ai', 'Bytespider', 'Amazonbot']
for bot in known_ai_bots:
    if f'User-agent: {bot}' in robots:
        # Find next Disallow
        section_match = re.search(rf'User-agent:\s*{re.escape(bot)}.*?(?=User-agent:|$)', robots, re.DOTALL)
        if section_match:
            section = section_match.group(0)
            if 'Disallow: /' in section and 'Disallow: /\n' in section:
                ai_bot_blocked.append(bot)
            else:
                ai_bot_allowed.append(bot)
    else:
        # Not explicitly listed = default policy (usually allow)
        ai_bot_allowed.append(bot + ' (default)')

print(f'  AI bots allowed: {ai_bot_allowed}')
print(f'  AI bots blocked: {ai_bot_blocked}')

print('\n=== [6] BLOG INVENTORY (from sitemap parse) ===')
try:
    blog_urls = [u for u in urls if '/blog' in u and u != f'{BASE}/blog']
    print(f'  Total blog posts: {len(blog_urls)}')
    print(f'  Recent (last 10):')
    for u in blog_urls[-10:]:
        print(f'    - {u.replace(BASE, "")}')
except Exception:
    pass

print('\n=== [7] HF dataset list verification ===')
hf_url = 'https://huggingface.co/api/datasets?author=neogenesislab&limit=20'
status, data, _ = fetch(hf_url)
try:
    datasets = json.loads(data)
    print(f'  HF datasets owned by neogenesislab: {len(datasets)}')
    for d in datasets[:20]:
        downloads = d.get('downloads', 0)
        likes = d.get('likes', 0)
        last_mod = d.get('lastModified', '?')[:10]
        print(f'    - {d.get("id"):60s} dl={downloads:>5d} likes={likes} mod={last_mod}')
except Exception as e:
    print(f'  parse err: {e}')
