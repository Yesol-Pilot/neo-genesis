#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT_DIR = path.join(ROOT, 'data', 'sbu-growth');
const DEFAULT_SITES = 'toolpick,aiforge,craftdesk,deploystack,finstack,sellkit';

const SITES = {
  toolpick: { name: 'ToolPick', domain: 'https://toolpick.dev' },
  aiforge: { name: 'AIForge', domain: 'https://aiforge.neogenesis.app' },
  craftdesk: { name: 'CraftDesk', domain: 'https://craftdesk.neogenesis.app' },
  deploystack: { name: 'DeployStack', domain: 'https://deploystack.neogenesis.app' },
  finstack: { name: 'FinStack', domain: 'https://finstack.neogenesis.app' },
  sellkit: { name: 'SellKit', domain: 'https://sellkit.neogenesis.app' },
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

async function fetchText(url) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      redirect: 'follow',
      headers: { 'user-agent': 'neo-sbu-topic-hub-live-audit/1.0' },
    });
    return { ok: response.ok, status: response.status, text: await response.text() };
  } catch (error) {
    return { ok: false, status: 0, text: '', error: String(error?.message || error) };
  } finally {
    clearTimeout(timeout);
  }
}

function firstTopicPath(sitemapText) {
  const match = sitemapText.match(/https?:\/\/[^<]+\/blog\/topics\/([a-z0-9-]+)/);
  return match ? `/blog/topics/${match[1]}` : '';
}

async function auditSite(siteId) {
  const site = SITES[siteId];
  if (!site) throw new Error(`Unsupported site: ${siteId}`);

  const topicsPath = '/blog/topics';
  const sitemap = await fetchText(`${site.domain}/sitemap.xml`);
  const topics = await fetchText(`${site.domain}${topicsPath}`);
  const clusterPath = firstTopicPath(sitemap.text);
  const cluster = clusterPath ? await fetchText(`${site.domain}${clusterPath}`) : { ok: false, status: 0, text: '' };

  const issues = [];
  if (!topics.ok) issues.push('topics_page_unreachable');
  if (!sitemap.ok || !sitemap.text.includes('/blog/topics')) issues.push('sitemap_missing_topics');
  if (!clusterPath) issues.push('sitemap_missing_topic_cluster');
  if (clusterPath && !cluster.ok) issues.push('topic_cluster_unreachable');

  return {
    site: siteId,
    name: site.name,
    domain: site.domain,
    topics: {
      url: `${site.domain}${topicsPath}`,
      status: topics.status,
      ok: topics.ok,
      hasHubCopy: /Topic Hubs|SaaS Topic Hubs|Research map/.test(topics.text),
    },
    sitemap: {
      url: `${site.domain}/sitemap.xml`,
      status: sitemap.status,
      ok: sitemap.ok,
      hasTopics: sitemap.text.includes('/blog/topics'),
    },
    firstCluster: {
      path: clusterPath,
      status: cluster.status,
      ok: cluster.ok,
      hasCanonicalHint: /rel=["']canonical["']/.test(cluster.text),
    },
    status: issues.length ? 'yellow' : 'green',
    issues,
  };
}

function markdown(report) {
  const lines = [
    '# SBU Topic Hub Live Audit',
    '',
    `- generatedAt: ${report.generatedAt}`,
    `- passed: ${report.passed}`,
    '',
    '| Site | Status | Topics | Sitemap | First Cluster |',
    '|---|---:|---:|---:|---:|',
  ];
  for (const site of report.sites) {
    lines.push(
      `| ${site.name} | ${site.status} | ${site.topics.status} | ${site.sitemap.hasTopics ? 'included' : 'missing'} | ${site.firstCluster.status} |`,
    );
  }
  return `${lines.join('\n')}\n`;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const siteIds = args.sites.split(',').map((site) => site.trim()).filter(Boolean);
  const report = {
    generatedAt: nowKst(),
    sites: [],
  };
  for (const site of siteIds) report.sites.push(await auditSite(site));
  report.passed = report.sites.every((site) => site.status === 'green');

  fs.mkdirSync(OUT_DIR, { recursive: true });
  const stamp = report.generatedAt.replace(/[:+]/g, '-');
  fs.writeFileSync(path.join(OUT_DIR, `topic-hub-live-${stamp}.json`), JSON.stringify(report, null, 2), 'utf8');
  fs.writeFileSync(path.join(OUT_DIR, `topic-hub-live-${stamp}.md`), markdown(report), 'utf8');
  fs.writeFileSync(path.join(OUT_DIR, 'topic-hub-live-latest.json'), JSON.stringify(report, null, 2), 'utf8');
  fs.writeFileSync(path.join(OUT_DIR, 'topic-hub-live-latest.md'), markdown(report), 'utf8');

  console.log(JSON.stringify(report, null, 2));
  if (!report.passed) process.exit(1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
