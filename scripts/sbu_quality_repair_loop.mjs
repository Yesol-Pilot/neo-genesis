#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT_DIR = path.join(ROOT, 'data', 'sbu-growth');
const DEFAULT_SITES = 'toolpick,aiforge,craftdesk,deploystack,finstack,sellkit';
const MIN_WORDS = 650;
const MARKER = 'sbu-quality-repair-loop';

const SITES = {
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
    maxWeakPerSite: 8,
    maxClusters: 25,
    maxInternalLinksPerSite: 25,
    since: todayKst(),
    dryRun: false,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--sites') args.sites = argv[++i] || args.sites;
    else if (arg === '--max-weak-per-site') args.maxWeakPerSite = Number(argv[++i] || args.maxWeakPerSite);
    else if (arg === '--max-clusters') args.maxClusters = Number(argv[++i] || args.maxClusters);
    else if (arg === '--max-internal-links-per-site') args.maxInternalLinksPerSite = Number(argv[++i] || args.maxInternalLinksPerSite);
    else if (arg === '--since') args.since = argv[++i] || args.since;
    else if (arg === '--dry-run') args.dryRun = true;
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

function todayKst() {
  return nowKst().slice(0, 10);
}

function siteDir(siteId) {
  return path.join(ROOT, 'src', 'sbu', siteId);
}

function blogDir(siteId) {
  return path.join(siteDir(siteId), 'content', 'blog');
}

function stripYamlQuotes(value) {
  return String(value || '')
    .trim()
    .replace(/^['"]/, '')
    .replace(/['"]$/, '')
    .trim();
}

function parseFrontmatter(text) {
  text = text.replace(/^\uFEFF/, '');
  const match = text.match(/^---\s*\r?\n([\s\S]*?)\r?\n---\s*/);
  if (!match) return { frontmatter: {}, body: text, prefix: '' };

  const frontmatter = {};
  for (const line of match[1].split(/\r?\n/)) {
    const keyValue = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (!keyValue) continue;
    frontmatter[keyValue[1]] = stripYamlQuotes(keyValue[2]);
  }

  return {
    frontmatter,
    body: text.slice(match[0].length),
    prefix: match[0],
  };
}

function upsertUpdatedDate(text, date) {
  text = text.replace(/^\uFEFF/, '');
  const match = text.match(/^---\s*\r?\n([\s\S]*?)\r?\n---\s*/);
  if (!match) return text;

  const block = match[1];
  const nextBlock = /^updatedDate:/m.test(block)
    ? block.replace(/^updatedDate:.*$/m, `updatedDate: "${date}"`)
    : `${block.trimEnd()}\nupdatedDate: "${date}"`;

  return `---\n${nextBlock}\n---\n${text.slice(match[0].length).replace(/^\r?\n/, '')}`;
}

function wordCount(text) {
  const { body } = parseFrontmatter(text);
  return body
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/[^\p{L}\p{N}'-]+/gu, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;
}

function hasInternalLink(text) {
  return /\]\(\/(?!\/)/.test(text);
}

function topicSlug(value) {
  return String(value || 'general')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '') || 'general';
}

function markdownText(value) {
  return String(value || '')
    .replace(/[\[\]]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function attr(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/"/g, '&quot;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .trim();
}

function normalizeTitle(title) {
  return String(title || '')
    .toLowerCase()
    .replace(/\b20\d{2}\b/g, '')
    .replace(/\b(best|top|guide|review|comparison|tools|platforms|software|for|in|and|the|a|an|to|vs)\b/g, ' ')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

function listPosts(siteId) {
  const dir = blogDir(siteId);
  if (!fs.existsSync(dir)) return [];

  return fs
    .readdirSync(dir)
    .filter((name) => name.endsWith('.mdx'))
    .map((name) => {
      const file = path.join(dir, name);
      const text = fs.readFileSync(file, 'utf8');
      const { frontmatter } = parseFrontmatter(text);
      return {
        site: siteId,
        siteName: SITES[siteId].name,
        domain: SITES[siteId].domain,
        file,
        slug: name.replace(/\.mdx$/, ''),
        title: frontmatter.title || name.replace(/\.mdx$/, ''),
        description: frontmatter.description || '',
        date: String(frontmatter.date || '').slice(0, 10),
        category: frontmatter.category || 'General',
        tags: frontmatter.tags || '',
        draft: String(frontmatter.draft || '').toLowerCase() === 'true',
        words: wordCount(text),
        text,
      };
    })
    .sort((a, b) => b.date.localeCompare(a.date) || a.slug.localeCompare(b.slug));
}

function recentInternalLinkBlock(post) {
  const category = markdownText(post.category);
  const categorySlug = topicSlug(post.category);

  return `

{/* ${MARKER}:recent-internal-link */}

## Related Research Paths

Use the [${category} topic hub](/blog/topics/${categorySlug}) when the search intent is still broad, or return to the [blog index](/blog) when the next decision depends on a different product category. Keeping this page linked to the surrounding research map helps readers compare adjacent options without treating every nearby article as the same recommendation.
`;
}

function weakExpansionBlock(post) {
  const title = markdownText(post.title);
  const category = markdownText(post.category);
  const cluster = topicSlug(post.category);

  return `

{/* ${MARKER}:weak-depth */}

## Practical Evaluation Depth

This page is now scoped as a practical decision brief for ${title}. Use it when the team needs a fast but defensible way to decide whether the category belongs in the current operating stack, whether it should stay on a watchlist, or whether it should be excluded before procurement and implementation time are wasted.

### When This Page Is the Right Fit

Start here when the question is not simply "what exists?" but "what should a working team do next?" For ${category} research, the useful decision usually depends on four constraints: the workflow owner, the implementation surface, the reporting requirement, and the cost of switching later. A tool that looks strong in a generic feature table can still be a poor fit if it requires new governance work, duplicates an existing workflow, or creates a data path the team cannot monitor.

Use this article as an intake screen before opening vendor demos or building a shortlist. The best reader is a founder, operator, product lead, engineering lead, or growth owner who has to translate a broad market category into a concrete action. If the team only needs definitions, the [blog index](/blog) is enough. If the team is comparing adjacent categories, use the [${category} topic hub](/blog/topics/${cluster}) to move through related pages without losing the original intent.

### Evaluation Checklist

Score each candidate on the same operating questions. First, identify the workflow it improves and the team that will own it after launch. Second, check whether the output is measurable inside existing analytics, CRM, finance, support, or product systems. Third, decide whether setup can be completed with existing data access and security rules. Fourth, define what would make the tool a clear failure after thirty days. A good shortlist has a kill condition, not only a promise.

For buyer-intent content, the strongest options normally show three traits. They reduce manual review work, expose a clear audit trail, and make the next action easier to choose. Weak options often create attractive dashboards without changing the weekly operating rhythm. Treat those as research references, not default purchases.

### Implementation Notes

Run a small pilot before committing to a broad rollout. Give the pilot one owner, one success metric, and one weekly checkpoint. If the tool cannot produce a visible improvement in the selected workflow during that window, keep the learning and stop expansion. If it works, document the handoff path, the reporting cadence, and the fallback process before adding more users.

The practical next step is to build a two-column shortlist: "adopt now" and "monitor later." Put only the options with clear ownership, measurable output, and low switching risk in the first column. Everything else can remain useful research without consuming implementation bandwidth.

<InlineCTA variant="calculator" toolName="${attr(category)} stack" categorySlug="${attr(cluster)}" />
`;
}

function intentRoutingBlock(post, cluster, siblings) {
  const title = markdownText(post.title);
  const key = markdownText(cluster.key);
  const clusterSlug = topicSlug(cluster.key);
  const category = markdownText(post.category);
  const categorySlug = topicSlug(post.category);
  const links = siblings
    .filter((sibling) => sibling.slug !== post.slug || sibling.site !== post.site)
    .slice(0, 5)
    .map((sibling) => {
      const sameSite = sibling.site === post.site;
      const href = sameSite ? `/blog/${sibling.slug}` : `${SITES[sibling.site].domain}/blog/${sibling.slug}`;
      return `- [${markdownText(sibling.title)}](${href}) - use this when the search intent is closer to ${markdownText(sibling.title).toLowerCase()}.`;
    });

  return `

{/* ${MARKER}:intent-routing:${clusterSlug} */}

## Search Intent Routing

This article is intentionally scoped to **${title}**. It should rank for readers who need this specific angle inside the broader **${key}** cluster, not for every adjacent query in the category. If the reader needs a wider map, start from the [${category} topic hub](/blog/topics/${categorySlug}) and then choose the page that matches the buying or implementation question.

Use this page when the decision depends on the exact framing in the title. Use a related page when the team is asking a different question, such as platform selection, tool comparison, security review, governance, cost monitoring, automation, or implementation planning.

${links.length ? links.join('\n') : `- [${category} topic hub](/blog/topics/${categorySlug}) - use this when the search intent is still broad.`}

The goal is to keep this page focused: one decision, one audience, one next action. That separation helps readers and crawlers distinguish this article from nearby cluster pages instead of treating the cluster as interchangeable duplicates.
`;
}

function buildClusters(posts, maxClusters) {
  const groups = new Map();
  for (const post of posts) {
    if (post.draft) continue;
    const key = normalizeTitle(post.title);
    if (key.length < 8) continue;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(post);
  }

  return Array.from(groups.entries())
    .filter(([, values]) => values.length > 1)
    .map(([key, values]) => ({ key, count: values.length, posts: values }))
    .sort((a, b) => b.count - a.count)
    .slice(0, maxClusters);
}

function appendBlock(post, block, marker, dryRun) {
  if (post.text.includes(marker)) return false;
  const next = `${upsertUpdatedDate(post.text.trimEnd(), todayKst())}${block}\n`;
  if (!dryRun) fs.writeFileSync(post.file, next, 'utf8');
  post.text = next;
  post.words = wordCount(next);
  return true;
}

function markdownReport(report) {
  const lines = [
    '# SBU Quality Repair Loop',
    '',
    `- generatedAt: ${report.generatedAt}`,
    `- dryRun: ${report.dryRun}`,
    `- filesChanged: ${report.filesChanged}`,
    `- weakPostsExpanded: ${report.weakPostsExpanded}`,
    `- internalLinksAdded: ${report.internalLinksAdded}`,
    `- intentRoutesAdded: ${report.intentRoutesAdded}`,
    `- clustersRouted: ${report.clustersRouted}`,
    `- since: ${report.since}`,
    '',
    '| Site | Weak Expanded | Internal Links | Intent Routes | Files Changed |',
    '|---|---:|---:|---:|---:|',
  ];

  for (const site of report.sites) {
    lines.push(`| ${site.site} | ${site.weakPostsExpanded} | ${site.internalLinksAdded} | ${site.intentRoutesAdded} | ${site.filesChanged} |`);
  }

  lines.push('', '## Routed Clusters', '');
  for (const cluster of report.routedClusters.slice(0, 30)) {
    lines.push(`- ${cluster.key}: ${cluster.count} posts`);
  }

  return `${lines.join('\n')}\n`;
}

function writeReport(report) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const stamp = report.generatedAt.replace(/[:+]/g, '-');
  fs.writeFileSync(path.join(OUT_DIR, `quality-repair-${stamp}.json`), JSON.stringify(report, null, 2), 'utf8');
  fs.writeFileSync(path.join(OUT_DIR, `quality-repair-${stamp}.md`), markdownReport(report), 'utf8');
  fs.writeFileSync(path.join(OUT_DIR, 'quality-repair-latest.json'), JSON.stringify(report, null, 2), 'utf8');
  fs.writeFileSync(path.join(OUT_DIR, 'quality-repair-latest.md'), markdownReport(report), 'utf8');
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const siteIds = args.sites.split(',').map((site) => site.trim()).filter(Boolean);
  const allPosts = siteIds.flatMap(listPosts);
  const siteStats = new Map(siteIds.map((site) => [site, {
    site,
    weakPostsExpanded: 0,
    internalLinksAdded: 0,
    intentRoutesAdded: 0,
    filesChanged: 0,
  }]));
  const changedFiles = new Set();

  for (const siteId of siteIds) {
    const weakPosts = allPosts
      .filter((post) => post.site === siteId && !post.draft && post.words < MIN_WORDS)
      .slice(0, args.maxWeakPerSite);

    for (const post of weakPosts) {
      const changed = appendBlock(post, weakExpansionBlock(post), `${MARKER}:weak-depth`, args.dryRun);
      if (!changed) continue;
      const stats = siteStats.get(siteId);
      stats.weakPostsExpanded += 1;
      stats.filesChanged += 1;
      changedFiles.add(post.file);
    }

    const internalLinkPosts = allPosts
      .filter((post) => post.site === siteId && !post.draft && post.date >= args.since && !hasInternalLink(post.text))
      .slice(0, args.maxInternalLinksPerSite);

    for (const post of internalLinkPosts) {
      const changed = appendBlock(post, recentInternalLinkBlock(post), `${MARKER}:recent-internal-link`, args.dryRun);
      if (!changed) continue;
      const stats = siteStats.get(siteId);
      stats.internalLinksAdded += 1;
      if (!changedFiles.has(post.file)) stats.filesChanged += 1;
      changedFiles.add(post.file);
    }
  }

  const clusters = buildClusters(allPosts, args.maxClusters);
  for (const cluster of clusters) {
    for (const post of cluster.posts) {
      const marker = `${MARKER}:intent-routing:${topicSlug(cluster.key)}`;
      const changed = appendBlock(post, intentRoutingBlock(post, cluster, cluster.posts), marker, args.dryRun);
      if (!changed) continue;
      const stats = siteStats.get(post.site);
      stats.intentRoutesAdded += 1;
      if (!changedFiles.has(post.file)) stats.filesChanged += 1;
      changedFiles.add(post.file);
    }
  }

  const report = {
    generatedAt: nowKst(),
    dryRun: args.dryRun,
    sites: Array.from(siteStats.values()),
    filesChanged: changedFiles.size,
    weakPostsExpanded: Array.from(siteStats.values()).reduce((sum, site) => sum + site.weakPostsExpanded, 0),
    internalLinksAdded: Array.from(siteStats.values()).reduce((sum, site) => sum + site.internalLinksAdded, 0),
    intentRoutesAdded: Array.from(siteStats.values()).reduce((sum, site) => sum + site.intentRoutesAdded, 0),
    clustersRouted: clusters.length,
    since: args.since,
    routedClusters: clusters.map((cluster) => ({
      key: cluster.key,
      count: cluster.count,
      sites: Array.from(new Set(cluster.posts.map((post) => post.site))),
    })),
  };

  writeReport(report);
  console.log(JSON.stringify(report, null, 2));
}

main();
