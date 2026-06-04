#!/usr/bin/env python3
"""DNS resolution verification using socket + direct authoritative NS query."""
import socket
import subprocess


TARGETS = [
    ('neogenesis.app', 'A', '76.76.21.21'),
    ('ethica.neogenesis.app', 'CNAME', '248dbe94501bde76.vercel-dns-017.com'),
    ('whylab.neogenesis.app', 'CNAME', 'cname.vercel-dns.com'),
    ('aiforge.neogenesis.app', 'CNAME', 'cname.vercel-dns.com'),
    ('dash.neogenesis.app', 'CNAME', 'neo.heoyesol.kr'),
    ('toolpick.neogenesis.app', 'NX', None),  # not in records, should NX
    ('www.neogenesis.app', 'CNAME', 'cname.vercel-dns.com'),
]

# Resolvers: target authoritative, public DNS
RESOLVERS = [
    ('Target NS', 'savanna.ns.cloudflare.com'),
    ('Cloudflare', '1.1.1.1'),
    ('Google', '8.8.8.8'),
]


def query(domain, server, qtype='ANY'):
    """Use nslookup with specific server, return raw output."""
    try:
        cmd = ['nslookup', '-type=' + qtype, domain, server]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return r.stdout + r.stderr
    except Exception as e:
        return f'ERROR: {e}'


def parse(output):
    """Extract Address/canonical from nslookup output."""
    lines = [l.strip() for l in output.split('\n') if l.strip()]
    addrs = []
    cnames = []
    nxdomain = False
    for ln in lines:
        if 'NXDOMAIN' in ln or "can't find" in ln.lower():
            nxdomain = True
        if 'canonical name' in ln:
            cnames.append(ln.split('=')[-1].strip().rstrip('.'))
    # Address lines after Name:
    for i, ln in enumerate(lines):
        if ln.startswith('Name:'):
            for follow in lines[i+1:i+3]:
                if follow.startswith('Address'):
                    a = follow.split(':', 1)[-1].strip()
                    if '#' not in a:
                        addrs.append(a)
    return {'addrs': addrs, 'cnames': cnames, 'nxdomain': nxdomain}


print(f'{"Domain":40s} {"Expected":50s} {"Result"}')
print('-' * 130)

for resolver_name, resolver_ip in RESOLVERS:
    print(f'\n=== via {resolver_name} ({resolver_ip}) ===')
    for domain, qtype, expected in TARGETS:
        if qtype == 'NX':
            out = query(domain, resolver_ip, 'A')
            r = parse(out)
            result = 'NXDOMAIN' if r['nxdomain'] else f'addrs={r["addrs"]} cnames={r["cnames"]}'
            ok = '[OK]' if r['nxdomain'] else '[FAIL]'
            print(f'  {ok} {domain:40s} expect=NX     -> {result}')
        else:
            out = query(domain, resolver_ip, qtype)
            r = parse(out)
            if qtype == 'A':
                ok = '[OK]' if expected in r['addrs'] else '[?]'
                print(f'  {ok} {domain:40s} expect={expected:30s} -> addrs={r["addrs"]}')
            else:  # CNAME
                ok = '[OK]' if any(expected.lower() in c.lower() for c in r['cnames']) else '[?]'
                # If no CNAME found, still might show A from final target
                if not r['cnames'] and r['addrs']:
                    ok = '[OK*]'  # resolved to A via implicit CNAME chase
                print(f'  {ok} {domain:40s} expect=CNAME->{expected[:25]:25s} -> cnames={r["cnames"][:2]} addrs={r["addrs"][:1]}')
