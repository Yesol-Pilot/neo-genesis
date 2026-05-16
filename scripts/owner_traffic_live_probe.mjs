#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const ROOT = path.resolve(path.dirname(__filename), '..');
const OUT_DIR = path.join(ROOT, 'data', 'owner-analytics');
const REGISTRY_PATH = path.join(OUT_DIR, 'site_registry.json');
const OUT_PATH = path.join(OUT_DIR, 'live-tag-probe-latest.json');
const KST_OFFSET_MS = 9 * 60 * 60 * 1000;

function kstNow() {
  return new Date(Date.now() + KST_OFFSET_MS).toISOString().replace('Z', '+09:00');
}

function atomicWriteJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const tmpPath = `${filePath}.${process.pid}.tmp`;
  fs.writeFileSync(tmpPath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  fs.renameSync(tmpPath, filePath);
}

function readRegistry() {
  if (!fs.existsSync(REGISTRY_PATH)) {
    throw new Error(`registry missing: ${path.relative(ROOT, REGISTRY_PATH)}. Run owner_traffic_command.mjs once first.`);
  }
  const registry = JSON.parse(fs.readFileSync(REGISTRY_PATH, 'utf8'));
  return (registry.sites ?? []).filter((site) => site.status === 'active_live' && site.canonical_url);
}

function unique(values) {
  return Array.from(new Set(values.filter(Boolean)));
}

const GA4_PATTERN = /googletagmanager\.com\/gtag\/js|gtag\s*\(/;
const POSTHOG_PATTERN = /posthog(?:\.init|\.capture)|us\.i\.posthog\.com|phc_[A-Za-z0-9]/;
const POSTHOG_KEY_PATTERN = /phc_[A-Za-z0-9]/;

function extractScriptUrls(html, baseUrl) {
  const urls = [];
  for (const match of html.matchAll(/<script\b[^>]*\bsrc=["']([^"']+)["'][^>]*>/gi)) {
    try {
      const parsed = new URL(match[1], baseUrl);
      if (/\/_next\/static\/|\/assets\/[^?#]+\.js(?:$|[?#])|googletagmanager|posthog/i.test(parsed.toString())) {
        urls.push(parsed.toString());
      }
    } catch {
      // Ignore malformed script URLs from third-party snippets.
    }
  }
  return unique(urls).slice(0, 48);
}

async function probeScripts(scriptUrls) {
  let posthogScriptHit = false;
  let keyScriptHit = false;
  let checked = 0;
  const errors = [];

  for (const scriptUrl of scriptUrls) {
    try {
      const response = await fetch(scriptUrl, {
        redirect: 'follow',
        signal: AbortSignal.timeout(10000),
        headers: {
          'User-Agent': 'OwnerTrafficCommand/1.0 (+https://neogenesis.app)',
          Accept: 'application/javascript,text/javascript,*/*',
        },
      });
      if (!response.ok) {
        errors.push(`${new URL(scriptUrl).pathname}: ${response.status}`);
        continue;
      }

      checked += 1;
      const text = await response.text();
      if (POSTHOG_PATTERN.test(text)) posthogScriptHit = true;
      if (POSTHOG_KEY_PATTERN.test(text)) keyScriptHit = true;
      if (posthogScriptHit && keyScriptHit) break;
    } catch (error) {
      errors.push(`${new URL(scriptUrl).pathname}: ${error.message}`);
    }
  }

  return { posthogScriptHit, keyScriptHit, checked, errors: errors.slice(0, 6) };
}

async function probeSite(site) {
  const started = Date.now();
  try {
    const response = await fetch(site.canonical_url, {
      redirect: 'follow',
      signal: AbortSignal.timeout(20000),
      headers: {
        'User-Agent': 'OwnerTrafficCommand/1.0 (+https://neogenesis.app)',
        Accept: 'text/html,application/xhtml+xml',
      },
    });
    const text = await response.text();
    const gaIds = unique(Array.from(text.matchAll(/\bG-[A-Z0-9]+\b/g)).map((match) => match[0]));
    const scriptUrls = extractScriptUrls(text, response.url);
    const htmlPosthogHit = POSTHOG_PATTERN.test(text);
    const htmlKeyHit = POSTHOG_KEY_PATTERN.test(text);
    const scriptProbe = htmlPosthogHit && htmlKeyHit
      ? { posthogScriptHit: false, keyScriptHit: false, checked: 0, errors: [] }
      : await probeScripts(scriptUrls);
    return {
      site_id: site.id,
      site_name: site.name,
      url: site.canonical_url,
      final_url: response.url,
      ok: response.ok,
      status: response.status,
      elapsed_ms: Date.now() - started,
      html_bytes: Buffer.byteLength(text, 'utf8'),
      ga4: {
        has_tag: GA4_PATTERN.test(text),
        measurement_ids: gaIds,
        expected_id_present: gaIds.includes('G-0GVNYZLEMX') || gaIds.length > 0,
      },
      posthog: {
        has_tag: htmlPosthogHit || scriptProbe.posthogScriptHit,
        key_present_redacted: htmlKeyHit || scriptProbe.keyScriptHit,
        html_has_tag: htmlPosthogHit,
        script_has_tag: scriptProbe.posthogScriptHit,
        scripts_checked: scriptProbe.checked,
      },
      errors: scriptProbe.errors,
    };
  } catch (error) {
    return {
      site_id: site.id,
      site_name: site.name,
      url: site.canonical_url,
      final_url: null,
      ok: false,
      status: null,
      elapsed_ms: Date.now() - started,
      html_bytes: 0,
      ga4: { has_tag: false, measurement_ids: [], expected_id_present: false },
      posthog: { has_tag: false, key_present_redacted: false },
      errors: [error.message],
    };
  }
}

async function main() {
  const sites = readRegistry();
  const rows = [];
  for (const site of sites) rows.push(await probeSite(site));
  const report = {
    generatedAt: kstNow(),
    source: 'owner_traffic_live_probe',
    sites: rows,
    summary: {
      sites: rows.length,
      live_ok: rows.filter((row) => row.ok).length,
      ga4_tag_present: rows.filter((row) => row.ga4.has_tag).length,
      posthog_tag_present: rows.filter((row) => row.posthog.has_tag).length,
    },
  };
  atomicWriteJson(OUT_PATH, report);
  console.log(JSON.stringify({ ok: true, path: path.relative(ROOT, OUT_PATH), summary: report.summary }, null, 2));
  if (!rows.every((row) => row.ok)) process.exitCode = 1;
}

main().catch((error) => {
  console.error(JSON.stringify({ ok: false, error: error.message }, null, 2));
  process.exit(1);
});
