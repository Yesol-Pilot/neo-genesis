#!/usr/bin/env python3
"""Probe what AI features are enableable on free plan for neogenesis.app zone."""
import os, json, urllib.request, urllib.error


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


def call(method, url, token, body=None):
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, headers=headers, method=method, data=data)
    try:
        r = urllib.request.urlopen(req, timeout=20)
        return r.status, json.loads(r.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8', errors='replace'))


env = load_env()
token = env['CF_API_TOKEN']
ZONE_ID = 'f123426af0f297cd7704a5759d3ec938'  # neogenesis.app target

# Read all zone settings to see what's available
print('=== ZONE SETTINGS (relevant subset) ===')
code, data = call('GET', f'https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/settings', token)
if isinstance(data, dict) and data.get('result'):
    settings = data['result']
    # Look for AI-related settings
    interesting = ['redirects_for_ai_training', 'markdown_for_agents', 'managed_robots_txt', 'bot_management', 'ai_crawl_control']
    for s in settings:
        sid = s.get('id', '')
        if any(k in sid.lower() for k in ['ai', 'robot', 'bot', 'crawl', 'markdown', 'redirect']):
            print(f'  {sid:40s} value={s.get("value")} editable={s.get("editable")} modified={s.get("modified_on")}')

print('\n=== Try PATCH redirects_for_ai_training ===')
code, data = call(
    'PATCH',
    f'https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/settings/redirects_for_ai_training',
    token,
    {'value': 'on'},
)
print(f'HTTP {code}')
if isinstance(data, dict):
    if data.get('success'):
        print(f'  SUCCESS: {data.get("result", {}).get("value")}')
    else:
        for e in data.get('errors', []):
            print(f'  err[{e.get("code")}]: {e.get("message")}')

print('\n=== Try PATCH markdown_for_agents (guessed endpoint) ===')
for endpoint in ('markdown_for_agents', 'markdown', 'agent_markdown'):
    code, data = call(
        'PATCH',
        f'https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/settings/{endpoint}',
        token,
        {'value': 'on'},
    )
    msg = ''
    if isinstance(data, dict):
        if data.get('success'):
            msg = f'SUCCESS: {data.get("result", {}).get("value")}'
        else:
            errs = data.get('errors', [])
            msg = errs[0].get('message', '')[:80] if errs else 'no errs'
    print(f'  PATCH /settings/{endpoint:30s} HTTP {code} | {msg}')

print('\n=== Try managed_robots_txt endpoints ===')
for endpoint in ('managed_robots_txt', 'robots_txt'):
    code, data = call(
        'PATCH',
        f'https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/settings/{endpoint}',
        token,
        {'value': 'on'},
    )
    msg = ''
    if isinstance(data, dict):
        if data.get('success'):
            msg = 'SUCCESS'
        else:
            errs = data.get('errors', [])
            msg = errs[0].get('message', '')[:80] if errs else 'no errs'
    print(f'  PATCH /settings/{endpoint:30s} HTTP {code} | {msg}')
