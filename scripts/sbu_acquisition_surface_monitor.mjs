#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT_DIR = path.join(ROOT, 'data', 'sbu-growth');
const DEFAULT_TARGETS = path.join(OUT_DIR, 'acquisition-surface-targets.json');

function parseArgs(argv) {
  const args = {
    targets: DEFAULT_TARGETS,
    timeoutMs: 30000,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--targets') args.targets = path.resolve(argv[++i] || args.targets);
    else if (arg === '--timeout-ms') args.timeoutMs = Number(argv[++i] || args.timeoutMs);
  }
  return args;
}

function kstNow() {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}T${values.hour}:${values.minute}:${values.second}+09:00`;
}

function stampFromIso(value) {
  return value.replace(/:/g, '-').replace(/\+09-00$/, '+09-00');
}

async function fetchText(url, timeoutMs) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, {
      headers: {
        'user-agent': 'neo-sbu-acquisition-surface-monitor/1.0',
        accept: 'text/html,application/xml,text/plain,*/*',
      },
      redirect: 'follow',
      signal: controller.signal,
    });
    return {
      ok: response.ok,
      status: response.status,
      url: response.url,
      text: await response.text(),
      error: null,
    };
  } catch (error) {
    return {
      ok: false,
      status: 0,
      url,
      text: '',
      error: String(error?.message || error),
    };
  } finally {
    clearTimeout(timeout);
  }
}

function extractTitle(html) {
  return (html.match(/<title[^>]*>(.*?)<\/title>/is)?.[1] || '').replace(/\s+/g, ' ').trim();
}

function extractDescription(html) {
  const match =
    html.match(/<meta[^>]+name=["']description["'][^>]+content=(["'])(.*?)\1/is) ||
    html.match(/<meta[^>]+content=(["'])(.*?)\1[^>]+name=["']description["']/is);
  return (match?.[2] || '').replace(/\s+/g, ' ').trim();
}

function extractCanonical(html) {
  const match =
    html.match(/<link[^>]+rel=["']canonical["'][^>]+href=(["'])(.*?)\1/is) ||
    html.match(/<link[^>]+href=(["'])(.*?)\1[^>]+rel=["']canonical["']/is);
  return (match?.[2] || '').trim();
}

function jsonLdCount(html) {
  return (html.match(/application\/ld\+json/gi) || []).length;
}

function pathIsBlockedByRobots(robotsText, pathname) {
  const rules = [];
  let applies = false;
  for (const rawLine of robotsText.split(/\r?\n/)) {
    const line = rawLine.replace(/#.*/, '').trim();
    if (!line) continue;
    const [rawKey, ...rawValueParts] = line.split(':');
    const key = rawKey.trim().toLowerCase();
    const value = rawValueParts.join(':').trim();
    if (key === 'user-agent') {
      applies = value === '*';
    } else if (applies && (key === 'allow' || key === 'disallow')) {
      rules.push({ type: key, path: value || '/' });
    }
  }

  const matching = rules
    .filter((rule) => rule.path && pathname.startsWith(rule.path))
    .sort((a, b) => b.path.length - a.path.length);
  if (!matching.length) return false;
  return matching[0].type === 'disallow';
}

function scoreChecks(checks) {
  const weights = {
    pageOk: 20,
    titleOk: 10,
    descriptionOk: 10,
    canonicalOk: 10,
    jsonLdOk: 10,
    expectedCopyOk: 15,
    sitemapOk: 15,
    robotsOk: 5,
    indexNowKeyOk: 5,
  };
  return Object.entries(weights).reduce((sum, [key, weight]) => sum + (checks[key] ? weight : 0), 0);
}

function criticalPass(checks) {
  return Boolean(checks.pageOk && checks.titleOk && checks.descriptionOk && checks.canonicalOk && checks.expectedCopyOk && checks.sitemapOk && checks.robotsOk);
}

async function inspectSurface(surface, config, timeoutMs) {
  const page = await fetchText(surface.url, timeoutMs);
  const sitemap = await fetchText(surface.sitemap, timeoutMs);
  const robots = await fetchText(surface.robots, timeoutMs);
  const indexNowUrl = `${new URL(surface.url).origin}/${config.indexNowKey}.txt`;
  const indexNow = config.indexNowKey ? await fetchText(indexNowUrl, timeoutMs) : { ok: true, status: 0, text: '', error: null };
  const pathname = new URL(surface.url).pathname;
  const expectedCopyMissing = surface.expectedPhrases.filter((phrase) => !page.text.includes(phrase));
  const canonical = extractCanonical(page.text);
  const title = extractTitle(page.text);
  const description = extractDescription(page.text);
  const checks = {
    pageOk: page.status === 200,
    titleOk: title.length >= 20,
    descriptionOk: description.length >= 80,
    canonicalOk: canonical === surface.url,
    jsonLdOk: jsonLdCount(page.text) >= 1,
    expectedCopyOk: expectedCopyMissing.length === 0,
    sitemapOk: sitemap.ok && sitemap.text.includes(surface.url),
    robotsOk: robots.ok && !pathIsBlockedByRobots(robots.text, pathname),
    indexNowKeyOk: !config.indexNowKey || (indexNow.ok && indexNow.text.trim() === config.indexNowKey),
  };
  const score = scoreChecks(checks);
  const pass = criticalPass(checks) && score >= 85;
  const trackerHints = {
    posthogStaticHint: /posthog|phc_|i\/v0\/e/i.test(page.text),
    gaStaticHint: /gtag|googletagmanager|G-[A-Z0-9]+/i.test(page.text),
    expectedEvent: surface.posthogEvent || null,
  };

  return {
    ...surface,
    checkedAt: kstNow(),
    pass,
    score,
    checks,
    page: {
      status: page.status,
      finalUrl: page.url,
      title,
      titleLen: title.length,
      descriptionLen: description.length,
      canonical,
      jsonLdCount: jsonLdCount(page.text),
      expectedCopyMissing,
      error: page.error,
    },
    sitemap: {
      status: sitemap.status,
      included: checks.sitemapOk,
      error: sitemap.error,
    },
    robots: {
      status: robots.status,
      blocked: !checks.robotsOk,
      error: robots.error,
    },
    indexNow: {
      keyUrl: indexNowUrl,
      status: indexNow.status,
      keyOk: checks.indexNowKeyOk,
      error: indexNow.error,
    },
    trackerHints,
    nextAction: pass
      ? 'monitor_gsc_and_posthog_48h_then_expand_top_candidate'
      : 'fix_failed_surface_checks_before_expansion',
  };
}

function renderMarkdown(report) {
  const lines = [
    '# SBU Acquisition Surface Monitor',
    '',
    `Generated: ${report.generatedAt}`,
    `Targets: ${report.summary.targets}`,
    `Passed: ${report.summary.passed}/${report.summary.targets}`,
    `Average score: ${report.summary.averageScore}`,
    '',
    '## Surface Status',
    '',
    '| Site | Surface | Market | Score | Pass | Page | Sitemap | Robots | IndexNow | Missing Copy | Next Action |',
    '|---|---|---|---:|---:|---:|---:|---:|---:|---|---|',
  ];
  for (const row of report.surfaces) {
    lines.push(
      `| ${row.site} | ${row.name} | ${row.market} | ${row.score} | ${row.pass} | ${row.page.status} | ${row.sitemap.included} | ${!row.robots.blocked} | ${row.indexNow.keyOk} | ${row.page.expectedCopyMissing.join(', ') || '-'} | ${row.nextAction} |`,
    );
  }

  lines.push('', '## Next Expansion Queue', '');
  for (const row of report.surfaces) {
    lines.push(`### ${row.name}`, '');
    for (const candidate of row.nextExpansionCandidates) {
      lines.push(`- ${candidate.path}: ${candidate.intent} -> ${candidate.asset}`);
    }
    lines.push('');
  }

  lines.push('## Notes', '');
  lines.push('- ToolPick, UR WRONG, and NeoGenesis are intentionally excluded from this loop.');
  lines.push('- GSC search analytics will not show meaningful data immediately after launch; use this report for live readiness until 48-72h data exists.');
  lines.push('- PostHog static hints are informational; runtime capture still requires browser/network checks or API-side event queries.');
  return `${lines.join('\n')}\n`;
}

function writeReport(report) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const stamp = stampFromIso(report.generatedAt);
  const jsonText = `${JSON.stringify(report, null, 2)}\n`;
  const mdText = renderMarkdown(report);
  const outputs = {
    stampedJson: path.join(OUT_DIR, `acquisition-surface-monitor-${stamp}.json`),
    stampedMd: path.join(OUT_DIR, `acquisition-surface-monitor-${stamp}.md`),
    latestJson: path.join(OUT_DIR, 'acquisition-surface-monitor-latest.json'),
    latestMd: path.join(OUT_DIR, 'acquisition-surface-monitor-latest.md'),
  };
  fs.writeFileSync(outputs.stampedJson, jsonText);
  fs.writeFileSync(outputs.latestJson, jsonText);
  fs.writeFileSync(outputs.stampedMd, mdText);
  fs.writeFileSync(outputs.latestMd, mdText);
  return outputs;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const config = JSON.parse(fs.readFileSync(args.targets, 'utf8'));
  const surfaces = await Promise.all(config.surfaces.map((surface) => inspectSurface(surface, config, args.timeoutMs)));
  const generatedAt = kstNow();
  const report = {
    generatedAt,
    source: path.relative(ROOT, args.targets),
    excludes: config.defaultExcludes || [],
    summary: {
      targets: surfaces.length,
      passed: surfaces.filter((surface) => surface.pass).length,
      failed: surfaces.filter((surface) => !surface.pass).length,
      averageScore: Number((surfaces.reduce((sum, surface) => sum + surface.score, 0) / Math.max(1, surfaces.length)).toFixed(2)),
      readyToExpand: surfaces.filter((surface) => surface.pass).map((surface) => surface.id),
    },
    surfaces,
  };
  const outputs = writeReport(report);
  console.log(JSON.stringify({ pass: report.summary.failed === 0, summary: report.summary, outputs }, null, 2));
  if (report.summary.failed > 0) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
