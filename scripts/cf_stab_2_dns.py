#!/usr/bin/env python3
"""Stability check 2/4: DNS resolution for all 13 subdomains."""
import socket


SUBS = [
    ('neogenesis.app', 'apex'),
    ('www.neogenesis.app', 'www'),
    ('aiforge.neogenesis.app', 'AIForge'),
    ('craftdesk.neogenesis.app', 'CraftDesk'),
    ('deploystack.neogenesis.app', 'DeployStack'),
    ('finstack.neogenesis.app', 'FinStack'),
    ('profit.neogenesis.app', 'Profit'),
    ('review.neogenesis.app', 'ReviewLab'),
    ('sellkit.neogenesis.app', 'SellKit'),
    ('whylab.neogenesis.app', 'WhyLab'),
    ('ethica.neogenesis.app', 'EthicaAI (blind review hold)'),
    ('dash.neogenesis.app', 'CF Tunnel'),
    ('neo.heoyesol.kr', 'Tunnel target (heoyesol.kr zone)'),
]

print('=== DNS resolution (OS resolver) ===')
ok, fail = 0, 0
for domain, role in SUBS:
    try:
        addr = socket.gethostbyname(domain)
        ok += 1
        marker = '[OK]'
    except socket.gaierror as e:
        addr = f'FAIL {e}'
        fail += 1
        marker = '[FAIL]'
    print(f'  {marker:7s} {domain:35s} -> {addr:25s} | {role}')

print(f'\nSummary: {ok}/{ok+fail} resolved')
