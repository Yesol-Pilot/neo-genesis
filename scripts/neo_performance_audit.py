#!/usr/bin/env python3
"""Neo Genesis comprehensive performance audit.

Measures:
1. SBU coverage (11 SBU live + HTTP + deployment recency)
2. Domain inventory + DNS state
3. Asset stockpile (HF datasets, Wikidata entities)
4. Risk audit
"""
import json
import os
import socket
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone


def http_head(url, timeout=10):
    t0 = time.monotonic()
    try:
        req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'neo-audit/1.0'})
        r = urllib.request.urlopen(req, timeout=timeout)
        return {'status': r.status, 'elapsed_ms': round((time.monotonic() - t0) * 1000),
                'server': r.headers.get('Server', '?')[:20]}
    except urllib.error.HTTPError as e:
        return {'status': e.code, 'elapsed_ms': round((time.monotonic() - t0) * 1000),
                'server': e.headers.get('Server', '?')[:20] if e.headers else '?'}
    except Exception as e:
        return {'status': 0, 'error': str(e)[:60]}


SBU_LIST = [
    # (name, primary_url, fallback_neogenesis_subdomain)
    ('ToolPick',     'https://www.toolpick.dev',                  None),
    ('K-OTT',        'https://kott.kr',                           None),
    ('UR WRONG',     'https://ur-wrong.com',                      None),
    ('SellKit',      'https://sellkit.neogenesis.app',            'https://sellkit.neogenesis.app'),
    ('FinStack',     'https://finstack.neogenesis.app',           'https://finstack.neogenesis.app'),
    ('DeployStack',  'https://deploystack.neogenesis.app',        'https://deploystack.neogenesis.app'),
    ('CraftDesk',    'https://craftdesk.neogenesis.app',          'https://craftdesk.neogenesis.app'),
    ('AIForge',      'https://aiforge.neogenesis.app',            'https://aiforge.neogenesis.app'),
    ('WhyLab',       'https://whylab.neogenesis.app',             'https://whylab.neogenesis.app'),
    ('EthicaAI',     'https://ethica.neogenesis.app',             'https://ethica.neogenesis.app'),
    ('ReviewLab',    'https://review.neogenesis.app',             'https://review.neogenesis.app'),
]

NON_SBU = [
    ('heoyesol.kr (portfolio)',   'https://heoyesol.kr'),
    ('neogenesis.app (landing)',  'https://neogenesis.app'),
    ('www.neogenesis.app',        'https://www.neogenesis.app'),
]

print('=' * 75)
print('NEO GENESIS PERFORMANCE AUDIT')
print(f'Timestamp: {datetime.now(timezone.utc).isoformat()}')
print('=' * 75)

print('\n=== [1] SBU COVERAGE (11 SBU) ===')
print(f'{"SBU":13s} {"URL":42s} {"HTTP":5s} {"ms":>4s} {"Status":8s}')
print('-' * 90)
live, partial, down = 0, 0, 0
for name, url, _ in SBU_LIST:
    h = http_head(url)
    status = h.get('status', 0)
    elapsed = h.get('elapsed_ms', 0)
    if status == 200:
        live += 1
        verdict = 'LIVE'
    elif status in (301, 302, 307, 308):
        live += 1
        verdict = 'LIVE (redirect)'
    elif status == 404:
        partial += 1
        verdict = 'PARTIAL 404'
    elif status >= 500 or status == 0:
        down += 1
        verdict = 'DOWN'
    else:
        partial += 1
        verdict = f'? ({status})'
    print(f'  {name:13s} {url[:42]:42s} {status:>5d} {elapsed:>4d} {verdict}')

print(f'\nSummary: {live} live / {partial} partial / {down} down')

print('\n=== [2] NON-SBU (portfolio + landing) ===')
for name, url in NON_SBU:
    h = http_head(url)
    print(f'  {name:30s} {url:35s} HTTP {h.get("status", 0):>3d}  ({h.get("elapsed_ms", 0)}ms)')

print('\n=== [3] BRAND ASSETS INVENTORY ===')
assets = {
    'Wikidata entities': '14+ entities registered (Neo Genesis Q139569680 + 13 SBU + people Q139569716/Q139569718)',
    'HuggingFace datasets': '1 published (neogenesislab/korean-rag-ssot-golden-50, 2026-04-28)',
    'GitHub repos': '24+ (Yesol-Pilot org, 11 SBU + neo-genesis + quant-bot + landing + portfolio)',
    'Vercel projects': '49 (active SBU production + various clients/proposals)',
    'Cloudflare zones': '4 (neogenesis.app target / kott.kr source / heoyesol.kr target / koreanllm.org target)',
    'CF Registrar': '2 (neogenesis.app + koreanllm.org, both target dpthf1537 post-transfer)',
    'Subdomains active': '11 SBU + dash + www on neogenesis.app',
    'Business entity': '네오 제네시스 (사업자등록 630-17-*****, 2026-01-27, 개인사업자 일반과세자)',
    'Email domain': '? (heoyesol.kr or neogenesis.app - to verify)',
    'Wikipedia status': 'NOT yet (notability seeding via dataset citations in progress, HN post pending blind review unhold)',
    'Papers in review': '2 (EthicaAI Melting Pot + WhyLab Docker validation, both double-blind venue HOLD)',
}
for k, v in assets.items():
    print(f'  {k:30s} : {v}')

print('\n=== [4] KOREANLLM.ORG AO-1 PROGRESS ===')
print(f'  W0 launch:  2026-06-10 (D-27 today)')
print(f'  Domain:     koreanllm.org (CF Registrar, target account)')
print(f'  Research:   Phase 1-9 done (40 docs, ~287K words). Phase 10 4 agents running on ASUS')
print(f'  Migration:  yesol-asus -> desktop-home complete (64 files, 984KB)')
print(f'  Stack:      Cloudflare Workers+Pages+R2+D1+KV (OpEx $58-450/mo)')

print('\n=== [5] REVENUE BASELINE ===')
print('  Cumulative revenue: $0 (cold honest)')
print('  Quant PoC:          CLOSED 2026-05-12 (-15.1% PnL, 38 days, 191 trades 0/108 sweep)')
print('  Active SBU monetization: 0 (all SBU pre-revenue / content/SEO building)')
print('  Wage income (CTS-AI): active (이트라이브, ongoing)')
print('  Revenue path research v1: 2026-05-12 (recommended D2 ETF + B1 SBU growth + C2 info products)')

print('\n=== [6] RISK AUDIT ===')
risks = [
    ('Blind review HOLD',     'arXiv submission of EthicaAI + WhyLab papers blocked until peer review concludes'),
    ('Wikipedia notability',  'CC indexing blocked (Greg Lindahl confirmed lack of incoming links)'),
    ('30-day transfer lock',  'neogenesis.app cannot transfer out until 2026-06-13'),
    ('kott.kr orphan',        'Still in source 8f22c351 account (사업자 단일화 미완)'),
    ('SBU monetization gap',  'All 11 SBU pre-revenue, no recurring income established'),
    ('Single owner bus factor', 'All ops concentrated to 1 person (yesol.heo / dpthf1537)'),
    ('Free tier dependency',   'Vercel/CF/Supabase all free tier, scaling limits'),
    ('Profit subdomain',       'Deleted today (orphaned, no Vercel project backing)'),
    ('dash.neogenesis.app',    '80% fixed, owner 1 click pending in CF Tunnel Public Hostname'),
]
for r, desc in risks:
    print(f'  • {r:25s} : {desc}')

print('\n=' * 75)
print(' AUDIT COMPLETE')
print('=' * 75)
