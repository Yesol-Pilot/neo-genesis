#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT_DIR = path.join(ROOT, 'data', 'sbu-growth');
const DEFAULT_EXCLUDES = new Set(['toolpick', 'ur-wrong', 'neogenesis']);

const SITE_META = {
  aiforge: {
    name: 'AIForge',
    market: 'global',
    lane: 'AI builders',
    strategy: [
      'Ship an agent stack selector or evaluation checklist as a tryable tool.',
      'Distribute through GitHub, AI builder communities, and Product Hunt only after the demo is usable.',
    ],
  },
  craftdesk: {
    name: 'CraftDesk',
    market: 'global',
    lane: 'design/product workflow',
    strategy: [
      'Publish a Figma Community template or UX rapid-prototyping checklist.',
      'Create search pages around rapid prototyping, UI review, and design QA workflows.',
    ],
  },
  deploystack: {
    name: 'DeployStack',
    market: 'global',
    lane: 'developer/devops',
    strategy: [
      'Ship a CI/CD YAML generator or preview-environment cost checklist.',
      'Distribute via DEV, GitHub templates, and HN only when the artifact is directly usable.',
    ],
  },
  finstack: {
    name: 'FinStack',
    market: 'global',
    lane: 'finance ops',
    strategy: [
      'Narrow the product promise to Stripe reconciliation, invoice ops, or SaaS finance templates.',
      'Publish one practical calculator/template before adding more generic finance posts.',
    ],
  },
  sellkit: {
    name: 'SellKit',
    market: 'global',
    lane: 'ecommerce sellers',
    strategy: [
      'Exploit proven GSC intent: Printful alternatives, Stripe pricing, Printful pricing, and Gumroad review.',
      'Add Stripe fee and POD margin calculators, then seed ecommerce/POD communities with tracked URLs.',
    ],
  },
  reviewlab: {
    name: 'ReviewLab',
    market: 'korea',
    lane: 'Korean product review',
    strategy: [
      'Rewrite Korean title/description/H1 for comparison and purchase-review intent.',
      'Prioritize Naver Search Advisor checks and Korean FAQ/pros-cons/spec tables.',
    ],
  },
  kott: {
    name: 'K-OTT',
    market: 'korea',
    lane: 'Korean OTT decision',
    strategy: [
      'Build OTT price, plan, and monthly-watch decision hubs in Korean.',
      'Track Naver/Google Korean queries separately from owned/direct traffic.',
    ],
  },
  whylab: {
    name: 'WhyLab',
    market: 'global',
    lane: 'research/product proof',
    strategy: [
      'Treat current pages as credibility assets until a concrete user job is defined.',
      'Avoid broad MAU acquisition spend before a repeatable tool or decision workflow exists.',
    ],
  },
  ethicaai: {
    name: 'EthicaAI',
    market: 'global',
    lane: 'AI ethics research',
    strategy: [
      'Productize one practical artifact such as an AI risk checklist or model evaluation worksheet.',
      'Use research pages for authority, not direct MAU scaling, until activation is measurable.',
    ],
  },
};

function parseArgs(argv) {
  const args = {
    excludes: new Set(DEFAULT_EXCLUDES),
    minFullGscSites: 8,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--exclude') {
      args.excludes = new Set(
        String(argv[++i] || '')
          .split(',')
          .map((item) => item.trim().toLowerCase())
          .filter(Boolean),
      );
    } else if (arg === '--min-full-gsc-sites') {
      args.minFullGscSites = Number(argv[++i] || args.minFullGscSites);
    }
  }
  return args;
}

function readJson(filePath, fallback = null) {
  if (!fs.existsSync(filePath)) return fallback;
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
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

function normalizeName(value) {
  return String(value || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '');
}

function findLatestFullGscReport(minSites) {
  if (!fs.existsSync(OUT_DIR)) return null;
  const candidates = fs
    .readdirSync(OUT_DIR)
    .filter((name) => /^gsc-all-sbu-.*\.json$/.test(name))
    .map((name) => path.join(OUT_DIR, name))
    .map((file) => {
      try {
        const data = readJson(file);
        return { file, data, generatedAt: data?.generatedAt || '', sites: Number(data?.summary?.sites || 0) };
      } catch {
        return null;
      }
    })
    .filter((item) => item && item.sites >= minSites)
    .sort((a, b) => String(b.generatedAt).localeCompare(String(a.generatedAt)));
  return candidates[0] || null;
}

function ga4BySite(ga4) {
  const map = new Map();
  for (const [key, value] of Object.entries(ga4 || {})) {
    const normalized = normalizeName(key);
    for (const [siteId, meta] of Object.entries(SITE_META)) {
      if (normalized === normalizeName(meta.name) || normalized === normalizeName(siteId)) {
        map.set(siteId, value);
      }
    }
  }
  return map;
}

function posthogBySite(posthog) {
  const map = new Map();
  for (const row of posthog?.rows || []) {
    map.set(String(row.site || '').toLowerCase(), row);
  }
  return map;
}

function gscBySite(gsc) {
  const map = new Map();
  for (const site of gsc?.sites || []) {
    map.set(String(site.id || '').toLowerCase(), site);
  }
  return map;
}

function sumOpportunityImpressions(site) {
  return (site?.opportunities || []).reduce((sum, item) => sum + Number(item.impressions || 0), 0);
}

function topOpportunity(site) {
  const opportunity = [...(site?.opportunities || [])].sort((a, b) => Number(b.impressions || 0) - Number(a.impressions || 0))[0];
  if (!opportunity) return null;
  const topQuery = opportunity.queries?.[0]?.query || null;
  return {
    page: opportunity.page,
    impressions: Number(opportunity.impressions || 0),
    clicks: Number(opportunity.clicks || 0),
    averagePosition: Number(opportunity.averagePosition || 0),
    topQuery,
  };
}

function classify(row) {
  if (row.gsc.opportunityCount >= 5 || row.gsc.opportunityImpressions >= 20) return 'capture-now';
  if (row.posthog.users >= 30 || row.ga4.users7d >= 10) return 'distribution-validation';
  return 'productize-before-growth';
}

function scoreRow(row) {
  return Number(
    (
      row.gsc.opportunityImpressions * 2 +
      row.gsc.opportunityCount * 10 +
      row.posthog.users * 1.5 +
      row.posthog.pageviews +
      row.ga4.users7d * 1.5 +
      row.ga4.users28d * 0.4
    ).toFixed(2),
  );
}

function measurementWarnings(row) {
  const warnings = [];
  if (row.posthog.users >= 20 && row.ga4.users7d === 0) {
    warnings.push('PostHog shows recent users but GA4 7d is zero; verify property/hostname filtering and data freshness.');
  }
  if (row.gsc.opportunityCount === 0 && row.posthog.users >= 30) {
    warnings.push('Traffic exists without search opportunity; validate referral/direct source and bot filtering.');
  }
  return warnings;
}

function makeRows(args, sources) {
  const posthogMap = posthogBySite(sources.posthog);
  const ga4Map = ga4BySite(sources.ga4);
  const gscMap = gscBySite(sources.gsc);
  const rows = [];

  for (const [siteId, meta] of Object.entries(SITE_META)) {
    if (args.excludes.has(siteId)) continue;
    const posthog = posthogMap.get(siteId) || {};
    const ga4 = ga4Map.get(siteId) || {};
    const gsc = gscMap.get(siteId) || {};
    const row = {
      site: siteId,
      name: meta.name,
      market: meta.market,
      lane: meta.lane,
      posthog: {
        events: Number(posthog.events || 0),
        pageviews: Number(posthog.pageviews || 0),
        users: Number(posthog.users || 0),
        lastSeen: posthog.lastSeen || null,
      },
      ga4: {
        users7d: Number(ga4.users_7d || 0),
        views7d: Number(ga4.views_7d || 0),
        sessions7d: Number(ga4.sessions_7d || 0),
        users28d: Number(ga4.users_28d || 0),
        views28d: Number(ga4.views_28d || 0),
      },
      gsc: {
        propertyListed: Boolean(gsc.propertyListed),
        sitemapKnown: Boolean(gsc.gscSitemap?.known),
        rows: Number(gsc.searchAnalytics?.rows || 0),
        opportunityCount: (gsc.opportunities || []).length,
        opportunityImpressions: sumOpportunityImpressions(gsc),
        topOpportunity: topOpportunity(gsc),
      },
      strategy: meta.strategy,
    };
    row.stage = classify(row);
    row.score = scoreRow(row);
    row.measurementWarnings = measurementWarnings(row);
    rows.push(row);
  }

  return rows.sort((a, b) => b.score - a.score);
}

function makeMarkdown(report) {
  const lines = [
    '# SBU Real User Acquisition Dashboard',
    '',
    `Generated: ${report.generatedAt}`,
    `Excluded: ${report.scope.excluded.join(', ')}`,
    '',
    '## Source Integrity',
    '',
    `- GSC source: ${report.sources.gsc.path || 'missing'}`,
    `- GSC generatedAt: ${report.sources.gsc.generatedAt || 'missing'}`,
    `- PostHog source: ${report.sources.posthog.path || 'missing'}`,
    `- GA4 source: ${report.sources.ga4.path || 'missing'}`,
    '',
    '## Priority Table',
    '',
    '| Rank | Site | Market | Stage | Score | PH Users | PH PV | GA4 7d Users | GSC Opps | GSC Impr | Top Query |',
    '|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|',
  ];

  report.rows.forEach((row, index) => {
    lines.push(
      `| ${index + 1} | ${row.name} | ${row.market} | ${row.stage} | ${row.score} | ${row.posthog.users} | ${row.posthog.pageviews} | ${row.ga4.users7d} | ${row.gsc.opportunityCount} | ${row.gsc.opportunityImpressions} | ${row.gsc.topOpportunity?.topQuery || '-'} |`,
    );
  });

  lines.push('', '## Action Queue', '');
  for (const row of report.rows) {
    lines.push(`### ${row.name}`, '');
    lines.push(`- lane: ${row.lane}`);
    lines.push(`- stage: ${row.stage}`);
    for (const action of row.strategy) lines.push(`- action: ${action}`);
    for (const warning of row.measurementWarnings) lines.push(`- measurement warning: ${warning}`);
    lines.push('');
  }

  return `${lines.join('\n')}\n`;
}

function writeReport(report) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const stamp = report.generatedAt.replace(/[:+]/g, '-');
  const json = `${JSON.stringify(report, null, 2)}\n`;
  const md = makeMarkdown(report);
  const paths = {
    stampedJson: path.join(OUT_DIR, `acquisition-dashboard-${stamp}.json`),
    stampedMd: path.join(OUT_DIR, `acquisition-dashboard-${stamp}.md`),
    latestJson: path.join(OUT_DIR, 'acquisition-dashboard-latest.json'),
    latestMd: path.join(OUT_DIR, 'acquisition-dashboard-latest.md'),
  };
  fs.writeFileSync(paths.stampedJson, json, 'utf8');
  fs.writeFileSync(paths.latestJson, json, 'utf8');
  fs.writeFileSync(paths.stampedMd, md, 'utf8');
  fs.writeFileSync(paths.latestMd, md, 'utf8');
  return paths;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const gscCandidate = findLatestFullGscReport(args.minFullGscSites);
  const posthogPath = path.join(OUT_DIR, 'posthog-traffic-latest.json');
  const ga4Path = path.join(ROOT, 'logs', 'ga4_result.json');
  const sources = {
    gsc: gscCandidate?.data || null,
    posthog: readJson(posthogPath, null),
    ga4: readJson(ga4Path, null),
  };
  const report = {
    generatedAt: kstNow(),
    scope: {
      excluded: [...args.excludes].sort(),
      sites: Object.keys(SITE_META).filter((siteId) => !args.excludes.has(siteId)),
    },
    sources: {
      gsc: {
        path: gscCandidate?.file ? path.relative(ROOT, gscCandidate.file) : null,
        generatedAt: gscCandidate?.data?.generatedAt || null,
        sites: gscCandidate?.sites || 0,
      },
      posthog: {
        path: fs.existsSync(posthogPath) ? path.relative(ROOT, posthogPath) : null,
        days: sources.posthog?.days || null,
      },
      ga4: {
        path: fs.existsSync(ga4Path) ? path.relative(ROOT, ga4Path) : null,
      },
    },
    rows: makeRows(args, sources),
  };
  report.summary = {
    siteCount: report.rows.length,
    captureNow: report.rows.filter((row) => row.stage === 'capture-now').length,
    distributionValidation: report.rows.filter((row) => row.stage === 'distribution-validation').length,
    productizeBeforeGrowth: report.rows.filter((row) => row.stage === 'productize-before-growth').length,
    totalPosthogUsers: report.rows.reduce((sum, row) => sum + row.posthog.users, 0),
    totalPosthogPageviews: report.rows.reduce((sum, row) => sum + row.posthog.pageviews, 0),
    totalGscOpportunityImpressions: report.rows.reduce((sum, row) => sum + row.gsc.opportunityImpressions, 0),
  };
  const paths = writeReport(report);
  console.log(JSON.stringify({
    passed: report.rows.length > 0,
    summary: report.summary,
    latestJson: paths.latestJson,
    latestMd: paths.latestMd,
  }, null, 2));
}

main();
