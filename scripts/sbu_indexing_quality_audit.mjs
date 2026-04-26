#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT_DIR = path.join(ROOT, 'data', 'sbu-growth');
const DEFAULT_SITES = 'finstack,sellkit';
const DEFAULT_SINCE = '2026-04-26';
const MIN_WORDS = 650;
const SAMPLE_SIZE = 5;

const SITE_CONFIG = {
  toolpick: { name: 'ToolPick', domain: 'https://toolpick.dev' },
  aiforge: { name: 'AIForge', domain: 'https://aiforge.neogenesis.app' },
  craftdesk: { name: 'CraftDesk', domain: 'https://craftdesk.neogenesis.app' },
  deploystack: { name: 'DeployStack', domain: 'https://deploystack.neogenesis.app' },
  finstack: { name: 'FinStack', domain: 'https://finstack.neogenesis.app' },
  sellkit: { name: 'SellKit', domain: 'https://sellkit.neogenesis.app' },
};

function parseArgs(argv) {
  const args = {
    sites: DEFAULT_SITES,
    since: DEFAULT_SINCE,
    sampleSize: SAMPLE_SIZE,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--sites') args.sites = argv[++i] || args.sites;
    else if (arg === '--since') args.since = argv[++i] || args.since;
    else if (arg === '--sample-size') args.sampleSize = Number(argv[++i] || SAMPLE_SIZE);
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

function parseFrontmatter(text) {
  if (!text.startsWith('---')) return {};
  const end = text.indexOf('\n---', 3);
  if (end === -1) return {};
  const block = text.slice(3, end).trim();
  const data = {};
  for (const line of block.split(/\r?\n/)) {
    const match = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (!match) continue;
    const key = match[1];
    let value = match[2].trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    data[key] = value;
  }
  return data;
}

function contentBody(text) {
  if (!text.startsWith('---')) return text;
  const end = text.indexOf('\n---', 3);
  return end === -1 ? text : text.slice(end + 4);
}

function wordCount(text) {
  return contentBody(text)
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/[#>*_[\]()`|:-]/g, ' ')
    .split(/\s+/)
    .filter(Boolean).length;
}

function hasCta(text) {
  return /<InlineCTA\b|buttonText=|buttonLink=/.test(text);
}

function hasInternalLink(text) {
  return /\]\(\/(?!\/)/.test(text);
}

function hasExternalLink(text) {
  return /\]\(https?:\/\//.test(text);
}

function listPosts(siteId, since) {
  const blogDir = path.join(ROOT, 'src', 'sbu', siteId, 'content', 'blog');
  return fs
    .readdirSync(blogDir)
    .filter((name) => name.endsWith('.mdx'))
    .map((name) => {
      const file = path.join(blogDir, name);
      const text = fs.readFileSync(file, 'utf8');
      const frontmatter = parseFrontmatter(text);
      const slug = name.replace(/\.mdx$/, '');
      const words = wordCount(text);
      const completeFrontmatter = ['title', 'date', 'description', 'category'].every(
        (key) => frontmatter[key],
      );
      return {
        slug,
        file: path.relative(ROOT, file),
        title: frontmatter.title || '',
        date: String(frontmatter.date || '').slice(0, 10),
        description: frontmatter.description || '',
        category: frontmatter.category || '',
        generatedBy: frontmatter.generatedBy || '',
        words,
        completeFrontmatter,
        hasCta: hasCta(text),
        hasInternalLink: hasInternalLink(text),
        hasExternalLink: hasExternalLink(text),
        qualityReady:
          completeFrontmatter && words >= MIN_WORDS && hasCta(text) && hasInternalLink(text),
      };
    })
    .filter((post) => post.date >= since)
    .sort((a, b) => b.date.localeCompare(a.date) || a.slug.localeCompare(b.slug));
}

async function fetchText(url) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 12000);
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      redirect: 'follow',
      headers: { 'user-agent': 'neo-sbu-indexing-quality-audit/1.0' },
    });
    const text = await response.text();
    return { ok: response.ok, status: response.status, text };
  } catch (error) {
    return { ok: false, status: 0, error: String(error?.message || error), text: '' };
  } finally {
    clearTimeout(timeout);
  }
}

function pct(numerator, denominator) {
  if (!denominator) return 0;
  return Number((numerator / denominator).toFixed(3));
}

async function auditSite(siteId, args) {
  const config = SITE_CONFIG[siteId];
  if (!config) throw new Error(`Unsupported site: ${siteId}`);

  const posts = listPosts(siteId, args.since);
  const sample = posts.slice(0, args.sampleSize);
  const sitemapUrl = `${config.domain}/sitemap.xml`;
  const robotsUrl = `${config.domain}/robots.txt`;
  const [sitemap, robots] = await Promise.all([fetchText(sitemapUrl), fetchText(robotsUrl)]);
  const liveSamples = [];

  for (const post of sample) {
    const url = `${config.domain}/blog/${post.slug}`;
    const page = await fetchText(url);
    liveSamples.push({
      slug: post.slug,
      url,
      status: page.status,
      ok: page.ok,
      hasTitle: post.title ? page.text.includes(post.title) : false,
      sitemapIncluded: sitemap.text.includes(`/blog/${post.slug}`),
      hasCanonicalHint: /rel=["']canonical["']/.test(page.text),
    });
  }

  const total = posts.length;
  const qualityReady = posts.filter((post) => post.qualityReady).length;
  const missingFrontmatter = posts.filter((post) => !post.completeFrontmatter);
  const tooShort = posts.filter((post) => post.words < MIN_WORDS);
  const missingCta = posts.filter((post) => !post.hasCta);
  const missingInternalLink = posts.filter((post) => !post.hasInternalLink);
  const liveFailures = liveSamples.filter((samplePost) => !samplePost.ok || !samplePost.sitemapIncluded);

  const issues = [];
  if (total === 0) issues.push('no_recent_posts');
  if (!sitemap.ok) issues.push('sitemap_unreachable');
  if (!robots.ok || !robots.text.includes('Sitemap:')) issues.push('robots_missing_sitemap');
  if (liveFailures.length) issues.push('live_sample_or_sitemap_failure');
  if (pct(qualityReady, total) < 0.9) issues.push('recent_quality_ready_below_90pct');

  return {
    site: siteId,
    name: config.name,
    domain: config.domain,
    since: args.since,
    totalRecentPosts: total,
    qualityReady,
    qualityReadyCoverage: pct(qualityReady, total),
    avgWords: total ? Math.round(posts.reduce((sum, post) => sum + post.words, 0) / total) : 0,
    coverage: {
      frontmatter: pct(posts.filter((post) => post.completeFrontmatter).length, total),
      cta: pct(posts.filter((post) => post.hasCta).length, total),
      internalLink: pct(posts.filter((post) => post.hasInternalLink).length, total),
      externalLink: pct(posts.filter((post) => post.hasExternalLink).length, total),
    },
    live: {
      sitemap: { ok: sitemap.ok, status: sitemap.status },
      robots: { ok: robots.ok, status: robots.status, hasSitemap: robots.text.includes('Sitemap:') },
      samples: liveSamples,
    },
    weakSamples: {
      missingFrontmatter: missingFrontmatter.slice(0, 5).map((post) => post.slug),
      tooShort: tooShort.slice(0, 5).map((post) => ({ slug: post.slug, words: post.words })),
      missingCta: missingCta.slice(0, 5).map((post) => post.slug),
      missingInternalLink: missingInternalLink.slice(0, 5).map((post) => post.slug),
    },
    status: issues.length ? 'yellow' : 'green',
    issues,
  };
}

function markdownReport(report) {
  const lines = [
    '# SBU Indexing Quality Audit',
    '',
    `- generatedAt: ${report.generatedAt}`,
    `- since: ${report.since}`,
    `- passed: ${report.passed}`,
    '',
    '| Site | Status | Recent Posts | Quality Ready | Avg Words | CTA | Internal | Sitemap | Live Samples |',
    '|---|---:|---:|---:|---:|---:|---:|---:|---:|',
  ];

  for (const site of report.sites) {
    const liveOk = site.live.samples.filter((sample) => sample.ok && sample.sitemapIncluded).length;
    lines.push(
      `| ${site.name} | ${site.status} | ${site.totalRecentPosts} | ${site.qualityReadyCoverage} | ${site.avgWords} | ${site.coverage.cta} | ${site.coverage.internalLink} | ${site.live.sitemap.ok ? 'ok' : 'fail'} | ${liveOk}/${site.live.samples.length} |`,
    );
  }

  lines.push('', '## Issues', '');
  const issueLines = report.sites.flatMap((site) =>
    site.issues.map((issue) => `- ${site.name}: ${issue}`),
  );
  lines.push(...(issueLines.length ? issueLines : ['- none']));

  return `${lines.join('\n')}\n`;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const sites = args.sites.split(',').map((site) => site.trim()).filter(Boolean);
  const report = {
    generatedAt: nowKst(),
    since: args.since,
    minWords: MIN_WORDS,
    sites: [],
  };

  for (const site of sites) {
    report.sites.push(await auditSite(site, args));
  }

  report.passed = report.sites.every((site) => site.status === 'green');
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const stamp = report.generatedAt.replace(/[:+]/g, '-');
  const jsonPath = path.join(OUT_DIR, `indexing-quality-${stamp}.json`);
  const mdPath = path.join(OUT_DIR, `indexing-quality-${stamp}.md`);
  fs.writeFileSync(jsonPath, JSON.stringify(report, null, 2), 'utf8');
  fs.writeFileSync(mdPath, markdownReport(report), 'utf8');
  fs.writeFileSync(path.join(OUT_DIR, 'indexing-quality-latest.json'), JSON.stringify(report, null, 2), 'utf8');
  fs.writeFileSync(path.join(OUT_DIR, 'indexing-quality-latest.md'), markdownReport(report), 'utf8');

  console.log(JSON.stringify(report, null, 2));
  if (!report.passed) process.exit(1);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
