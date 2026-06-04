#!/usr/bin/env python3
"""Log CF transfer completion to web_action_log.jsonl"""
import json
import os

entry = {
    "ts": "2026-05-14T15:55:00+09:00",
    "agent": "claude-opus-4.7",
    "action": "cf_inter_account_transfer_complete",
    "domain": "neogenesis.app",
    "src_acct": "8f22c351c93d878aacb918d9ee36a9c2",
    "dst_acct": "b3fa19c512029d0e847f77ea4d9b1fa2",
    "old_zone_id": "85380cbe940510fc1cf2620b1f24c707",
    "new_zone_id": "f123426af0f297cd7704a5759d3ec938",
    "new_ns": ["savanna.ns.cloudflare.com", "trevor.ns.cloudflare.com"],
    "old_ns": ["jerome.ns.cloudflare.com", "robin.ns.cloudflare.com"],
    "records_migrated": "14/14",
    "activated_on": "2026-05-14T06:05:44Z",
    "verification": {
        "socket_apex": "76.76.21.21",
        "https_4_sites": "HTTP 200 Vercel",
        "auth_ns_query": "OK",
    },
    "side_effects": "0 (11 SBU sites unaffected, Vercel deployments unchanged, SSL valid)",
    "owner_time": "~5min (token perm + zone create + Move Submit + Activate)",
    "transfer_lock_until": "2026-06-13 (30 days)",
    "status": "complete",
}

path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    '.agent', 'shared-brain', 'web_action_log.jsonl',
)
with open(path, 'a', encoding='utf-8') as f:
    f.write(json.dumps(entry, ensure_ascii=False) + '\n')

# Show count
with open(path, encoding='utf-8') as f:
    line_count = sum(1 for _ in f)
print(f'[logged] {path}: now {line_count} lines')
