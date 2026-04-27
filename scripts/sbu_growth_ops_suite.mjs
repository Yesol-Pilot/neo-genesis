#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT_DIR = path.join(ROOT, 'data', 'sbu-growth');
const DEFAULT_SITES = 'toolpick,aiforge,craftdesk,deploystack,finstack,sellkit';

const SITES = {
  toolpick: { name: 'ToolPick', domain: 'https://toolpick.dev', branch: 'master' },
  aiforge: { name: 'AIForge', domain: 'https://aiforge.neogenesis.app', branch: 'main' },
  craftdesk: { name: 'CraftDesk', domain: 'https://craftdesk.neogenesis.app', branch: 'main' },
  deploystack: { name: 'DeployStack', domain: 'https://deploystack.neogenesis.app', branch: 'main' },
  finstack: { name: 'FinStack', domain: 'https://finstack.neogenesis.app', branch: 'main' },
  sellkit: { name: 'SellKit', domain: 'https://sellkit.neogenesis.app', branch: 'main' },
};

function parseArgs(argv) {
  const args = { sites: DEFAULT_SITES };
  for (let i = 0; i < argv.length; i += 1) {
    if (argv[i] === '--sites') args.sites = argv[++i] || args.sites;
  }
  return args;
}

function nowKst() {
  const date = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).format(new Date());
  const time = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Asia/Seoul',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date());
  return `${date}T${time}+09:00`;
}

async function fetchText(url, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      redirect: 'follow',
      headers: { 'user-agent': 'neo-sbu-growth-ops-suite/1.0', ...(options.headers || {}) },
      method: options.method || 'GET',
    });
    return { ok: response.ok, status: response.status, text: await response.text() };
  } catch (error) {
    return { ok: false, status: 0, text: '', error: String(error?.message || error) };
  } finally {
    clearTimeout(timeout);
  }
}

function readIfExists(filePath) {
  return fs.existsSync(filePath) ? fs.readFileSync(filePath, 'utf8') : '';
}

function walkFiles(dir, predicate, limit = 5000) {
  const results = [];
  const stack = [dir];
  while (stack.length && results.length < limit) {
    const current = stack.pop();
    if (!current || !fs.existsSync(current)) continue;
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) {
        if (!['node_modules', '.next', '.git'].includes(entry.name)) stack.push(full);
      } else if (predicate(full)) {
        results.push(full);
      }
    }
  }
  return results;
}

function parseFrontmatter(text) {
  text = text.replace(/^\uFEFF/, '');
  if (!text.startsWith('---')) return {};
  const end = text.indexOf('\n---', 3);
  if (end === -1) return {};
  const data = {};
  for (const line of text.slice(3, end).trim().split(/\r?\n/)) {
    const match = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (!match) continue;
    let value = match[2].trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    data[match[1]] = value;
  }
  return data;
}

function wordCount(text) {
  text = text.replace(/^\uFEFF/, '');
  const body = text.startsWith('---') ? text.slice(text.indexOf('\n---', 3) + 4) : text;
  return body
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/[#>*_[\]()`|:-]/g, ' ')
    .split(/\s+/)
    .filter(Boolean).length;
}

function normalizeTitle(title) {
  return title
    .toLowerCase()
    .replace(/\b20\d{2}\b/g, '')
    .replace(/\b(best|top|guide|review|comparison|tools|platforms|software|for|in|and|the|a|an|to|vs)\b/g, ' ')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

function siteDir(siteId) {
  return path.join(ROOT, 'src', 'sbu', siteId);
}

function listPosts(siteId) {
  const blogDir = path.join(siteDir(siteId), 'content', 'blog');
  if (!fs.existsSync(blogDir)) return [];
  return fs
    .readdirSync(blogDir)
    .filter((name) => name.endsWith('.mdx'))
    .map((name) => {
      const file = path.join(blogDir, name);
      const text = fs.readFileSync(file, 'utf8');
      const data = parseFrontmatter(text);
      return {
        site: siteId,
        slug: name.replace(/\.mdx$/, ''),
        title: data.title || name.replace(/\.mdx$/, ''),
        description: data.description || '',
        category: data.category || '',
        date: String(data.date || '').slice(0, 10),
        words: wordCount(text),
        hasCta: /<InlineCTA\b|buttonText=|buttonLink=/.test(text),
        hasInternalLink: /\]\(\/(?!\/)/.test(text),
        hasIntentRouting: /sbu-quality-repair-loop:intent-routing/.test(text),
      };
    });
}

async function measurementIntegrity(siteIds) {
  const sites = [];
  for (const siteId of siteIds) {
    const config = SITES[siteId];
    const dir = siteDir(siteId);
    const codeFiles = walkFiles(path.join(dir, 'src'), (file) => /\.(ts|tsx|js|jsx)$/.test(file), 1200);
    const combined = codeFiles.map(readIfExists).join('\n');
    const home = await fetchText(config.domain);
    const liveText = home.text.slice(0, 250000);
    const hasPostHogCode = /posthog/i.test(combined);
    const hasGaCode = /gaId|gtag|GA_MEASUREMENT|G-|googletagmanager/i.test(combined);
    const hasPostHogLive = /posthog|phc_|ph_/.test(liveText);
    const hasGaLive = /gtag|G-[A-Z0-9]+|googletagmanager/i.test(liveText);
    const issues = [];
    if (!home.ok) issues.push('home_unreachable');
    if (!hasPostHogCode && !hasGaCode) issues.push('no_tracker_code_detected');
    if (!hasPostHogLive && !hasGaLive) issues.push('no_live_tracker_hint_detected');
    sites.push({
      site: siteId,
      name: config.name,
      homeStatus: home.status,
      code: { posthog: hasPostHogCode, ga: hasGaCode },
      live: { posthog: hasPostHogLive, ga: hasGaLive },
      status: issues.length ? 'yellow' : 'green',
      issues,
    });
  }
  return {
    passed: sites.every((site) => site.homeStatus === 200 && (site.code.posthog || site.code.ga)),
    sites,
  };
}

async function searchIndexing(siteIds) {
  const hasSearchConsoleCredentials = Boolean(
    process.env.GOOGLE_APPLICATION_CREDENTIALS ||
      process.env.GSC_SERVICE_ACCOUNT_JSON ||
      process.env.GOOGLE_SEARCH_CONSOLE_CLIENT_EMAIL,
  );
  const sites = [];
  for (const siteId of siteIds) {
    const config = SITES[siteId];
    const [sitemap, robots] = await Promise.all([
      fetchText(`${config.domain}/sitemap.xml`),
      fetchText(`${config.domain}/robots.txt`),
    ]);
    const issues = [];
    if (!sitemap.ok) issues.push('sitemap_unreachable');
    if (!robots.ok || !robots.text.includes('Sitemap:')) issues.push('robots_missing_sitemap');
    if (!sitemap.text.includes('/blog/')) issues.push('sitemap_missing_blog_urls');
    sites.push({
      site: siteId,
      name: config.name,
      sitemap: { status: sitemap.status, ok: sitemap.ok, blogUrls: (sitemap.text.match(/\/blog\//g) || []).length },
      robots: { status: robots.status, ok: robots.ok, hasSitemap: robots.text.includes('Sitemap:') },
      submission: hasSearchConsoleCredentials ? 'ready_for_submit' : 'dry_run_missing_gsc_credentials',
      status: issues.length ? 'yellow' : 'green',
      issues,
    });
  }
  return {
    passed: sites.every((site) => site.status === 'green'),
    hasSearchConsoleCredentials,
    sites,
  };
}

function cannibalization(siteIds) {
  const posts = siteIds.flatMap(listPosts);
  const groups = new Map();
  for (const post of posts) {
    const key = normalizeTitle(post.title);
    if (key.length < 8) continue;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(post);
  }
  const exactClusters = Array.from(groups.entries())
    .filter(([, values]) => values.length > 1)
    .map(([key, values]) => ({
      key,
      count: values.length,
      routed: values.every((post) => post.hasIntentRouting),
      sites: Array.from(new Set(values.map((post) => post.site))),
      samples: values.slice(0, 8).map((post) => ({
        site: post.site,
        slug: post.slug,
        title: post.title,
        hasIntentRouting: post.hasIntentRouting,
      })),
    }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 25);
  const unresolvedClusters = exactClusters.filter((cluster) => !cluster.routed);

  return {
    passed: true,
    totalPosts: posts.length,
    exactClusterCount: exactClusters.length,
    routedClusterCount: exactClusters.filter((cluster) => cluster.routed).length,
    unresolvedClusterCount: unresolvedClusters.length,
    topClusters: exactClusters,
    topUnresolvedClusters: unresolvedClusters,
  };
}

async function cronSmoke(siteIds) {
  const sites = [];
  for (const siteId of siteIds) {
    const config = SITES[siteId];
    const response = await fetchText(`${config.domain}/api/hive-mind/orchestrate`, { method: 'GET' });
    const protectedRoute = response.status === 401 || response.status === 403;
    const safeOk = protectedRoute || response.status === 405 || response.ok;
    const issues = [];
    if (!safeOk) issues.push('orchestrate_route_unexpected_status');
    if (response.ok) issues.push('orchestrate_get_executed_without_auth_review_needed');
    sites.push({
      site: siteId,
      name: config.name,
      statusCode: response.status,
      protectedRoute,
      safeSmokePassed: safeOk && !response.ok,
      status: issues.length ? 'yellow' : 'green',
      issues,
    });
  }
  return {
    passed: sites.every((site) => site.safeSmokePassed || site.statusCode === 405),
    sites,
  };
}

function eventTaxonomy(siteIds) {
  const sites = [];
  for (const siteId of siteIds) {
    const dir = siteDir(siteId);
    const codeFiles = walkFiles(path.join(dir, 'src'), (file) => /\.(ts|tsx)$/.test(file), 1200);
    const combined = codeFiles.map(readIfExists).join('\n');
    const posts = listPosts(siteId);
    const ctaCoverage = posts.length ? posts.filter((post) => post.hasCta).length / posts.length : 0;
    const hasPosthogEvents = /capture\(|track[A-Z]|posthogEvents|event-taxonomy|eventTaxonomy/i.test(combined);
    const hasTrackedLink = /TrackedLink|data-cta|buttonLink|InlineCTA/i.test(combined);
    const issues = [];
    if (!hasTrackedLink) issues.push('no_tracked_cta_component_hint');
    if (!hasPosthogEvents) issues.push('no_event_taxonomy_hint');
    sites.push({
      site: siteId,
      name: SITES[siteId].name,
      ctaCoverage: Number(ctaCoverage.toFixed(3)),
      hasTrackedLink,
      hasPosthogEvents,
      status: issues.length ? 'yellow' : 'green',
      issues,
    });
  }
  return {
    passed: sites.every((site) => site.hasTrackedLink),
    sites,
  };
}

function weeklyReport(siteIds, report) {
  const control = JSON.parse(readIfExists(path.join(OUT_DIR, 'control-tower-latest.json')) || '{"sites":[]}');
  const siteRows = siteIds.map((siteId) => {
    const site = control.sites?.find((candidate) => candidate.id === siteId);
    return {
      site: siteId,
      status: site?.status || 'unknown',
      modeledMau: site?.local?.posts?.modeledMau || 0,
      readyPosts: site?.local?.posts?.ready || 0,
      ctaCoverage: site?.local?.posts?.ctaCoverage || 0,
      internalLinkCoverage: site?.local?.posts?.internalLinkCoverage || 0,
      liveOk: Boolean(site?.live?.blog?.ok && site?.live?.detail?.ok && site?.live?.sitemap?.ok),
    };
  });
  return {
    passed: true,
    summary: {
      greenSites: siteRows.filter((site) => site.status === 'green').length,
      totalModeledMau: siteRows.reduce((sum, site) => sum + site.modeledMau, 0),
      liveOkSites: siteRows.filter((site) => site.liveOk).length,
    },
    siteRows,
    nextExperiments: [
      'Raise weak short-post samples above 650 words on each SBU.',
      'Add query-level Search Console opportunity ingestion once credentials are wired.',
      'Standardize PostHog event names across CTA, affiliate, and topic hub clicks.',
      'Use topic hub click-through data to pick the next 20 cluster expansion posts.',
    ],
    sourceReports: {
      controlTower: 'data/sbu-growth/control-tower-latest.json',
      topicHub: 'data/sbu-growth/topic-hub-live-latest.json',
      indexingQuality: 'data/sbu-growth/indexing-quality-latest.json',
    },
    warnings: {
      measurementYellow: report.measurement.sites.filter((site) => site.status !== 'green').length,
      eventTaxonomyYellow: report.eventTaxonomy.sites.filter((site) => site.status !== 'green').length,
      cannibalizationClusters: report.cannibalization.unresolvedClusterCount,
      rawCannibalizationClusters: report.cannibalization.exactClusterCount,
      routedCannibalizationClusters: report.cannibalization.routedClusterCount,
    },
  };
}

function markdown(report) {
  const lines = [
    '# SBU Growth Ops Suite',
    '',
    `- generatedAt: ${report.generatedAt}`,
    `- passed: ${report.passed}`,
    '',
    '## Gates',
    '',
    `- measurement integrity: ${report.measurement.passed}`,
    `- search indexing readiness: ${report.searchIndexing.passed}`,
    `- cannibalization audit generated: ${report.cannibalization.passed}`,
    `- safe cron smoke: ${report.cronSmoke.passed}`,
    `- event taxonomy readiness: ${report.eventTaxonomy.passed}`,
    `- weekly report generated: ${report.weeklyReport.passed}`,
    '',
    '## Weekly Site Rows',
    '',
    '| Site | Status | Modeled MAU | Ready Posts | CTA | Internal | Live |',
    '|---|---:|---:|---:|---:|---:|---:|',
  ];

  for (const site of report.weeklyReport.siteRows) {
    lines.push(
      `| ${site.site} | ${site.status} | ${site.modeledMau} | ${site.readyPosts} | ${site.ctaCoverage} | ${site.internalLinkCoverage} | ${site.liveOk} |`,
    );
  }

  lines.push('', '## Next Experiments', '');
  for (const experiment of report.weeklyReport.nextExperiments) lines.push(`- ${experiment}`);
  lines.push('', '## Notes', '');
  lines.push(`- Search Console submit mode: ${report.searchIndexing.hasSearchConsoleCredentials ? 'ready' : 'dry-run; credentials not present in this shell'}`);
  lines.push(`- Cannibalization raw exact clusters found: ${report.cannibalization.exactClusterCount}`);
  lines.push(`- Cannibalization intent-routed clusters: ${report.cannibalization.routedClusterCount}`);
  lines.push(`- Cannibalization unresolved clusters: ${report.cannibalization.unresolvedClusterCount}`);
  lines.push(`- Measurement yellow sites: ${report.weeklyReport.warnings.measurementYellow}`);
  lines.push(`- Event taxonomy yellow sites: ${report.weeklyReport.warnings.eventTaxonomyYellow}`);
  return `${lines.join('\n')}\n`;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const siteIds = args.sites.split(',').map((site) => site.trim()).filter(Boolean);
  const report = { generatedAt: nowKst(), sites: siteIds };

  report.measurement = await measurementIntegrity(siteIds);
  report.searchIndexing = await searchIndexing(siteIds);
  report.cannibalization = cannibalization(siteIds);
  report.cronSmoke = await cronSmoke(siteIds);
  report.eventTaxonomy = eventTaxonomy(siteIds);
  report.weeklyReport = weeklyReport(siteIds, report);
  report.passed =
    report.searchIndexing.passed &&
    report.cannibalization.passed &&
    report.cronSmoke.passed &&
    report.weeklyReport.passed;

  fs.mkdirSync(OUT_DIR, { recursive: true });
  const stamp = report.generatedAt.replace(/[:+]/g, '-');
  fs.writeFileSync(path.join(OUT_DIR, `growth-ops-suite-${stamp}.json`), JSON.stringify(report, null, 2), 'utf8');
  fs.writeFileSync(path.join(OUT_DIR, `growth-ops-suite-${stamp}.md`), markdown(report), 'utf8');
  fs.writeFileSync(path.join(OUT_DIR, 'growth-ops-suite-latest.json'), JSON.stringify(report, null, 2), 'utf8');
  fs.writeFileSync(path.join(OUT_DIR, 'growth-ops-suite-latest.md'), markdown(report), 'utf8');

  console.log(JSON.stringify(report, null, 2));
  if (!report.passed) process.exit(1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
