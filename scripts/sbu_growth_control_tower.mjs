#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DEFAULT_OUTPUT_DIR = path.join(ROOT, 'data', 'sbu-growth');
const TARGET_MAU = 100000;
const MONTHLY_VISITS_PER_READY_POST = 350;
const REQUIRED_READY_POSTS = Math.ceil(TARGET_MAU / MONTHLY_VISITS_PER_READY_POST);
const FRESHNESS_MAX_DAYS = 1;
const MIN_READY_WORDS = 650;

const SITES = [
  {
    id: 'toolpick',
    name: 'ToolPick',
    domain: 'https://toolpick.dev',
    repo: 'Yesol-Pilot/https-www.toolpick.dev-',
    benchmark: true,
  },
  {
    id: 'aiforge',
    name: 'AIForge',
    domain: 'https://aiforge.neogenesis.app',
    repo: 'Yesol-Pilot/aiforge',
  },
  {
    id: 'craftdesk',
    name: 'CraftDesk',
    domain: 'https://craftdesk.neogenesis.app',
    repo: 'Yesol-Pilot/craftdesk',
  },
  {
    id: 'deploystack',
    name: 'DeployStack',
    domain: 'https://deploystack.neogenesis.app',
    repo: 'Yesol-Pilot/deploystack',
  },
  {
    id: 'finstack',
    name: 'FinStack',
    domain: 'https://finstack.neogenesis.app',
    repo: 'Yesol-Pilot/finstack',
  },
  {
    id: 'sellkit',
    name: 'SellKit',
    domain: 'https://sellkit.neogenesis.app',
    repo: 'Yesol-Pilot/sellkit',
  },
];

function parseArgs(argv) {
  const args = {
    sites: 'all',
    live: true,
    write: true,
    json: false,
    strict: false,
    outputDir: DEFAULT_OUTPUT_DIR,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--sites') args.sites = argv[++i] || 'all';
    else if (arg === '--no-live') args.live = false;
    else if (arg === '--no-write') args.write = false;
    else if (arg === '--json') args.json = true;
    else if (arg === '--strict') args.strict = true;
    else if (arg === '--output-dir') args.outputDir = path.resolve(argv[++i] || DEFAULT_OUTPUT_DIR);
  }

  return args;
}

function kstStamp() {
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

function todayKst() {
  return kstStamp().slice(0, 10);
}

function run(cmd, cmdArgs, cwd) {
  const result = spawnSync(cmd, cmdArgs, {
    cwd,
    encoding: 'utf8',
    shell: false,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  return {
    ok: result.status === 0,
    status: result.status,
    stdout: (result.stdout || '').trim(),
    stderr: (result.stderr || '').trim(),
  };
}

function readJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch {
    return null;
  }
}

function stripYamlQuotes(value) {
  return String(value)
    .trim()
    .replace(/^['"]/, '')
    .replace(/['"]$/, '')
    .trim();
}

function parseFrontmatter(text) {
  const match = text.match(/^---\s*\r?\n([\s\S]*?)\r?\n---\s*/);
  const frontmatter = {};
  let body = text;

  if (match) {
    body = text.slice(match[0].length);
    const lines = match[1].split(/\r?\n/);
    for (let i = 0; i < lines.length; i += 1) {
      const line = lines[i];
      const keyValue = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
      if (!keyValue) continue;
      const [, key, rawValue] = keyValue;
      if (!rawValue || rawValue.trim() === '') continue;
      const value = rawValue.trim();
      if (['>', '>-', '|', '|-'].includes(value)) {
        const folded = [];
        while (i + 1 < lines.length && /^\s+/.test(lines[i + 1])) {
          i += 1;
          folded.push(lines[i].trim());
        }
        frontmatter[key] = value.startsWith('>') ? folded.join(' ').trim() : folded.join('\n').trim();
      } else {
        frontmatter[key] = stripYamlQuotes(rawValue);
      }
    }
  }

  return { frontmatter, body };
}

function wordCount(text) {
  return text
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/[^\p{L}\p{N}'-]+/gu, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;
}

function extractPosts(siteDir) {
  const blogDir = path.join(siteDir, 'content', 'blog');
  if (!fs.existsSync(blogDir)) return [];

  return fs
    .readdirSync(blogDir)
    .filter((name) => name.endsWith('.mdx'))
    .map((name) => {
      const file = path.join(blogDir, name);
      const text = fs.readFileSync(file, 'utf8');
      const { frontmatter, body } = parseFrontmatter(text);
      const words = wordCount(body);
      const requiredFields = ['title', 'date', 'description', 'category'];
      const completeFrontmatter = requiredFields.every((field) => Boolean(frontmatter[field]));
      const draft = String(frontmatter.draft || '').toLowerCase() === 'true';
      const hasCta = /<InlineCTA\b|buttonLink=|buttonText=|\[.*?\]\(\/stacks\//.test(body);
      const hasInternalLink = /\]\(\/(?!\/)/.test(body);
      const hasExternalLink = /https?:\/\//.test(body);

      return {
        slug: name.replace(/\.mdx$/, ''),
        file: path.relative(ROOT, file),
        title: frontmatter.title || '',
        date: frontmatter.date || '',
        description: frontmatter.description || '',
        category: frontmatter.category || '',
        draft,
        words,
        completeFrontmatter,
        hasCta,
        hasInternalLink,
        hasExternalLink,
        ready: !draft && completeFrontmatter && /^\d{4}-\d{2}-\d{2}/.test(frontmatter.date || '') && words >= MIN_READY_WORDS,
      };
    })
    .sort((a, b) => {
      const dateCompare = String(b.date).localeCompare(String(a.date));
      return dateCompare || a.slug.localeCompare(b.slug);
    });
}

function daysSince(dateText, todayText) {
  if (!/^\d{4}-\d{2}-\d{2}/.test(dateText || '')) return null;
  const date = new Date(`${dateText.slice(0, 10)}T00:00:00+09:00`);
  const today = new Date(`${todayText}T00:00:00+09:00`);
  return Math.floor((today.getTime() - date.getTime()) / 86400000);
}

async function fetchText(url) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(url, { redirect: 'follow', signal: controller.signal });
    const text = await response.text();
    return { ok: response.ok, status: response.status, text };
  } catch (error) {
    return { ok: false, status: 0, error: error instanceof Error ? error.message : String(error), text: '' };
  } finally {
    clearTimeout(timer);
  }
}

async function inspectLive(site, latestPost) {
  if (!latestPost) {
    return {
      blog: { ok: false, status: 0, reason: 'no-local-post' },
      detail: { ok: false, status: 0, reason: 'no-local-post' },
      sitemap: { ok: false, status: 0, reason: 'no-local-post' },
      robots: { ok: false, status: 0, reason: 'no-local-post' },
    };
  }

  const [blog, detail, sitemap, robots] = await Promise.all([
    fetchText(`${site.domain}/blog`),
    fetchText(`${site.domain}/blog/${latestPost.slug}`),
    fetchText(`${site.domain}/sitemap.xml`),
    fetchText(`${site.domain}/robots.txt`),
  ]);

  return {
    blog: {
      ok: blog.ok && (blog.text.includes(latestPost.slug) || blog.text.includes(latestPost.title)),
      status: blog.status,
      hasSlug: blog.text.includes(latestPost.slug),
      hasTitle: blog.text.includes(latestPost.title),
    },
    detail: {
      ok: detail.ok && detail.text.includes(latestPost.title) && detail.text.includes(latestPost.date.slice(0, 10)),
      status: detail.status,
      hasTitle: detail.text.includes(latestPost.title),
      hasDate: detail.text.includes(latestPost.date.slice(0, 10)),
    },
    sitemap: {
      ok: sitemap.ok && sitemap.text.includes(`/blog/${latestPost.slug}`),
      status: sitemap.status,
      hasLatestSlug: sitemap.text.includes(`/blog/${latestPost.slug}`),
    },
    robots: {
      ok: robots.ok,
      status: robots.status,
      hasSitemap: /sitemap/i.test(robots.text),
    },
  };
}

function summarizeLocal(site, todayText) {
  const siteDir = path.join(ROOT, 'src', 'sbu', site.id);
  const packageJson = readJson(path.join(siteDir, 'package.json'));
  const vercelJson = readJson(path.join(siteDir, '.vercel', 'project.json'));
  const posts = extractPosts(siteDir);
  const latest = posts[0] || null;
  const readyPosts = posts.filter((post) => post.ready);
  const categories = new Set(posts.map((post) => post.category).filter(Boolean));
  const daysOld = latest ? daysSince(latest.date, todayText) : null;
  const remote = fs.existsSync(path.join(siteDir, '.git')) ? run('git', ['remote', '-v'], siteDir) : { ok: false, stdout: '' };
  const email = fs.existsSync(path.join(siteDir, '.git')) ? run('git', ['config', 'user.email'], siteDir) : { ok: false, stdout: '' };
  const status = fs.existsSync(path.join(siteDir, '.git')) ? run('git', ['status', '--short'], siteDir) : { ok: false, stdout: '' };

  const count = posts.length || 1;
  const ctaCoverage = posts.filter((post) => post.hasCta).length / count;
  const internalLinkCoverage = posts.filter((post) => post.hasInternalLink).length / count;
  const frontmatterCoverage = posts.filter((post) => post.completeFrontmatter).length / count;
  const avgWords = Math.round(posts.reduce((sum, post) => sum + post.words, 0) / count);
  const modeledMau = readyPosts.length * MONTHLY_VISITS_PER_READY_POST;

  return {
    siteDir: path.relative(ROOT, siteDir),
    exists: fs.existsSync(siteDir),
    package: {
      hasBuild: Boolean(packageJson?.scripts?.build),
      hasPostbuild: Boolean(packageJson?.scripts?.postbuild),
      name: packageJson?.name || '',
    },
    vercel: {
      hasProject: Boolean(vercelJson?.projectId && vercelJson?.orgId),
      projectId: vercelJson?.projectId || '',
      orgId: vercelJson?.orgId || '',
    },
    git: {
      remoteOk: Boolean(remote.stdout && remote.stdout.includes(site.repo)),
      emailOk: email.stdout === 'dpthf1537@gmail.com',
      dirty: Boolean(status.stdout),
      remoteSummary: remote.stdout.split(/\r?\n/).find((line) => line.includes('(push)')) || '',
      email: email.stdout,
      statusLineCount: status.stdout ? status.stdout.split(/\r?\n/).length : 0,
    },
    posts: {
      total: posts.length,
      ready: readyPosts.length,
      requiredFor100k: REQUIRED_READY_POSTS,
      additionalReadyNeeded: Math.max(0, REQUIRED_READY_POSTS - readyPosts.length),
      modeledMau,
      mauGap: Math.max(0, TARGET_MAU - modeledMau),
      latest,
      daysSinceLatest: daysOld,
      fresh: daysOld !== null && daysOld <= FRESHNESS_MAX_DAYS,
      categoryCount: categories.size,
      avgWords,
      frontmatterCoverage: Number(frontmatterCoverage.toFixed(3)),
      ctaCoverage: Number(ctaCoverage.toFixed(3)),
      internalLinkCoverage: Number(internalLinkCoverage.toFixed(3)),
      weakSamples: posts
        .filter((post) => !post.ready)
        .slice(0, 5)
        .map((post) => ({
          slug: post.slug,
          date: post.date,
          words: post.words,
          completeFrontmatter: post.completeFrontmatter,
          draft: post.draft,
        })),
    },
  };
}

function actionQueue(site, local, live) {
  const actions = [];
  if (!local.exists) actions.push('Restore missing local SBU directory before growth work.');
  if (!local.posts.fresh) actions.push('Run autonomous publisher: latest MDX is older than daily freshness gate.');
  if (local.posts.additionalReadyNeeded > 0) {
    actions.push(`Add ${local.posts.additionalReadyNeeded} promotion-ready posts to reach modeled 100k MAU capacity.`);
  }
  if (local.posts.ctaCoverage < 0.7) actions.push('Upgrade CTA coverage across existing posts.');
  if (local.posts.internalLinkCoverage < 0.6) actions.push('Add internal links and hub routes to improve crawl depth.');
  if (!local.package.hasBuild) actions.push('Restore package build script before deployment automation.');
  if (!local.vercel.hasProject) actions.push('Bind Vercel project metadata.');
  if (!local.git.remoteOk) actions.push(`Fix git remote: expected ${site.repo}.`);
  if (!local.git.emailOk) actions.push('Fix git user.email to dpthf1537@gmail.com.');
  if (local.git.dirty) actions.push('Review dirty working tree before automated publish/deploy.');
  if (live && !live.blog.ok) actions.push('Repair live blog listing for latest local post.');
  if (live && !live.detail.ok) actions.push('Repair live detail page rendering for latest local post.');
  if (live && !live.sitemap.ok) actions.push('Regenerate or redeploy sitemap with latest post URL.');
  if (live && !live.robots.hasSitemap) actions.push('Expose sitemap reference in robots.txt.');
  return actions;
}

function scoreSite(local, live) {
  const contentScore = Math.min(25, Math.round((local.posts.ready / REQUIRED_READY_POSTS) * 25));
  const freshnessScore = local.posts.fresh ? 15 : 0;
  const qualityScore = Math.round(
    Math.min(20, (local.posts.frontmatterCoverage * 8) + (local.posts.ctaCoverage * 6) + (local.posts.internalLinkCoverage * 4) + (local.posts.avgWords >= MIN_READY_WORDS ? 2 : 0)),
  );
  const opsScore = [local.package.hasBuild, local.package.hasPostbuild, local.vercel.hasProject, local.git.remoteOk, local.git.emailOk]
    .filter(Boolean).length * 2;
  const liveScore = live
    ? [live.blog.ok, live.detail.ok, live.sitemap.ok, live.robots.ok].filter(Boolean).length * 5
    : 20;
  return Math.min(100, contentScore + freshnessScore + qualityScore + opsScore + liveScore);
}

async function inspectSite(site, args, todayText) {
  const local = summarizeLocal(site, todayText);
  const live = args.live ? await inspectLive(site, local.posts.latest) : null;
  const actions = actionQueue(site, local, live);
  const score = scoreSite(local, live);

  return {
    id: site.id,
    name: site.name,
    domain: site.domain,
    benchmark: Boolean(site.benchmark),
    targetMau: TARGET_MAU,
    monthlyVisitsPerReadyPost: MONTHLY_VISITS_PER_READY_POST,
    score,
    status: score >= 85 && actions.length === 0 ? 'green' : score >= 65 ? 'yellow' : 'red',
    local,
    live,
    actions,
  };
}

function makeMarkdown(report) {
  const lines = [
    '# SBU Growth Control Tower',
    '',
    `- generatedAt: ${report.generatedAt}`,
    `- targetMauPerSite: ${report.targetMau}`,
    `- modeledMonthlyVisitsPerReadyPost: ${report.monthlyVisitsPerReadyPost}`,
    `- requiredReadyPostsFor100k: ${report.requiredReadyPosts}`,
    '',
    '## Scoreboard',
    '',
    '| Site | Status | Score | Posts | Ready | Modeled MAU | MAU Gap | Latest | Live | Top Action |',
    '|---|---:|---:|---:|---:|---:|---:|---|---|---|',
  ];

  for (const site of report.sites) {
    const latest = site.local.posts.latest;
    const liveOk = site.live
      ? [site.live.blog.ok, site.live.detail.ok, site.live.sitemap.ok].every(Boolean)
      : true;
    lines.push([
      site.name,
      site.status,
      site.score,
      site.local.posts.total,
      site.local.posts.ready,
      site.local.posts.modeledMau,
      site.local.posts.mauGap,
      latest ? `${latest.date} / ${latest.slug}` : 'none',
      liveOk ? 'ok' : 'fail',
      site.actions[0] || 'none',
    ].join(' | ').replace(/^/, '| ').replace(/$/, ' |'));
  }

  lines.push('', '## Site Details', '');
  for (const site of report.sites) {
    const latest = site.local.posts.latest;
    lines.push(
      `### ${site.name}`,
      '',
      `- domain: ${site.domain}`,
      `- status: ${site.status} (${site.score}/100)`,
      `- latestPost: ${latest ? `${latest.date} / ${latest.slug}` : 'none'}`,
      `- freshnessDays: ${site.local.posts.daysSinceLatest ?? 'unknown'}`,
      `- posts: ${site.local.posts.total} total, ${site.local.posts.ready} promotion-ready`,
      `- modeledMau: ${site.local.posts.modeledMau}, gap: ${site.local.posts.mauGap}`,
      `- quality: frontmatter ${site.local.posts.frontmatterCoverage}, CTA ${site.local.posts.ctaCoverage}, internalLinks ${site.local.posts.internalLinkCoverage}, avgWords ${site.local.posts.avgWords}`,
      `- ops: build=${site.local.package.hasBuild}, vercel=${site.local.vercel.hasProject}, remote=${site.local.git.remoteOk}, email=${site.local.git.emailOk}, dirty=${site.local.git.dirty}`,
    );
    if (site.live) {
      lines.push(`- live: blog=${site.live.blog.ok}, detail=${site.live.detail.ok}, sitemap=${site.live.sitemap.ok}, robots=${site.live.robots.ok}`);
    }
    lines.push('- actions:');
    for (const action of site.actions.length ? site.actions : ['none']) {
      lines.push(`  - ${action}`);
    }
    lines.push('');
  }

  return `${lines.join('\n')}\n`;
}

function writeReport(report, outputDir) {
  fs.mkdirSync(outputDir, { recursive: true });
  const safeStamp = report.generatedAt.replace(/[:+]/g, '-');
  const json = JSON.stringify(report, null, 2);
  const markdown = makeMarkdown(report);
  fs.writeFileSync(path.join(outputDir, 'control-tower-latest.json'), `${json}\n`, 'utf8');
  fs.writeFileSync(path.join(outputDir, 'control-tower-latest.md'), markdown, 'utf8');
  fs.writeFileSync(path.join(outputDir, `control-tower-${safeStamp}.json`), `${json}\n`, 'utf8');
  fs.writeFileSync(path.join(outputDir, `control-tower-${safeStamp}.md`), markdown, 'utf8');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const selectedIds = args.sites === 'all'
    ? null
    : new Set(args.sites.split(',').map((site) => site.trim()).filter(Boolean));
  const selectedSites = selectedIds ? SITES.filter((site) => selectedIds.has(site.id)) : SITES;
  const generatedAt = kstStamp();
  const todayText = todayKst();

  const sites = [];
  for (const site of selectedSites) {
    sites.push(await inspectSite(site, args, todayText));
  }

  const report = {
    generatedAt,
    today: todayText,
    targetMau: TARGET_MAU,
    monthlyVisitsPerReadyPost: MONTHLY_VISITS_PER_READY_POST,
    requiredReadyPosts: REQUIRED_READY_POSTS,
    liveChecked: args.live,
    sites,
  };

  if (args.write) writeReport(report, args.outputDir);

  if (args.json) {
    console.log(JSON.stringify(report, null, 2));
  } else {
    console.log(makeMarkdown(report));
  }

  const failing = sites.filter((site) => site.status === 'red' || site.actions.some((action) => /Repair|Restore|Fix/.test(action)));
  if (args.strict && failing.length > 0) process.exit(1);
}

main().catch((error) => {
  console.error(error instanceof Error ? error.stack || error.message : String(error));
  process.exit(1);
});
