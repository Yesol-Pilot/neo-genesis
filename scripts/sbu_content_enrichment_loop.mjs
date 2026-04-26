#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const TARGET_CTA_COVERAGE = 0.72;
const TARGET_INTERNAL_LINK_COVERAGE = 0.65;

const SITES = {
  toolpick: {
    name: 'ToolPick',
    ctaDescription: 'Explore more software buying guides, comparisons, and stack decisions on ToolPick.',
  },
  aiforge: {
    name: 'AIForge',
    ctaDescription: 'Explore more AI tooling and agent workflow guides on AIForge.',
  },
  craftdesk: {
    name: 'CraftDesk',
    ctaDescription: 'Explore more design workflow and creative automation guides on CraftDesk.',
  },
  deploystack: {
    name: 'DeployStack',
    ctaDescription: 'Explore more deployment, observability, and DevOps stack guides on DeployStack.',
  },
  finstack: {
    name: 'FinStack',
    ctaDescription: 'Explore more fintech infrastructure and financial workflow guides on FinStack.',
  },
  sellkit: {
    name: 'SellKit',
    ctaDescription: 'Explore more ecommerce growth and sales workflow guides on SellKit.',
  },
};

function parseArgs(argv) {
  const args = {
    sites: 'toolpick,aiforge,craftdesk,deploystack,finstack,sellkit',
    dryRun: false,
    limit: null,
    targetCtaCoverage: TARGET_CTA_COVERAGE,
    targetInternalLinkCoverage: TARGET_INTERNAL_LINK_COVERAGE,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--sites') args.sites = argv[++i] || args.sites;
    else if (arg === '--dry-run') args.dryRun = true;
    else if (arg === '--limit') args.limit = Number(argv[++i] || 0);
    else if (arg === '--target-cta') args.targetCtaCoverage = Number(argv[++i] || TARGET_CTA_COVERAGE);
    else if (arg === '--target-internal') args.targetInternalLinkCoverage = Number(argv[++i] || TARGET_INTERNAL_LINK_COVERAGE);
  }
  return args;
}

function parseFrontmatterDate(text) {
  const match = text.match(/^date:\s*['"]?([^'"\r\n]+)['"]?/m);
  return match ? match[1].trim().slice(0, 10) : '';
}

function hasCta(text) {
  return /<InlineCTA\b|buttonLink=|buttonText=/.test(text);
}

function hasInternalLink(text) {
  return /\]\(\/(?!\/)/.test(text);
}

function listPosts(siteId) {
  const blogDir = path.join(ROOT, 'src', 'sbu', siteId, 'content', 'blog');
  return fs
    .readdirSync(blogDir)
    .filter((name) => name.endsWith('.mdx'))
    .map((name) => {
      const file = path.join(blogDir, name);
      const text = fs.readFileSync(file, 'utf8');
      return {
        slug: name.replace(/\.mdx$/, ''),
        file,
        relFile: path.relative(ROOT, file),
        date: parseFrontmatterDate(text),
        text,
        hasCta: hasCta(text),
        hasInternalLink: hasInternalLink(text),
        alreadyEnriched: text.includes('sbu-content-enrichment-loop'),
      };
    })
    .sort((a, b) => {
      const aNeeds = Number(!a.hasCta) + Number(!a.hasInternalLink);
      const bNeeds = Number(!b.hasCta) + Number(!b.hasInternalLink);
      return bNeeds - aNeeds || String(b.date).localeCompare(String(a.date)) || a.slug.localeCompare(b.slug);
    });
}

function coverage(posts, key) {
  if (posts.length === 0) return 0;
  return posts.filter((post) => post[key]).length / posts.length;
}

function requiredAdds(total, covered, target) {
  return Math.max(0, Math.ceil(total * target) - covered);
}

function buildAddition(site, needsCta, needsInternalLink) {
  const lines = [];
  lines.push('', '{/* sbu-content-enrichment-loop */}');
  if (needsInternalLink) {
    lines.push(
      '',
      '## Continue the Evaluation',
      '',
      `For adjacent buying guides, use the [${site.name} blog hub](/blog) to compare related workflows before committing budget or changing the operating stack.`,
    );
  }
  if (needsCta) {
    lines.push(
      '',
      '<InlineCTA',
      `  title="Compare more ${site.name} guides"`,
      `  description="${site.ctaDescription.replace(/"/g, '\\"')}"`,
      '  buttonText="Explore Blog"',
      '  buttonLink="/blog"',
      '/>',
    );
  }
  lines.push('');
  return lines.join('\n');
}

function enrichSite(siteId, args) {
  const site = SITES[siteId];
  if (!site) throw new Error(`Unsupported site: ${siteId}`);

  const posts = listPosts(siteId);
  const ctaCovered = posts.filter((post) => post.hasCta).length;
  const internalCovered = posts.filter((post) => post.hasInternalLink).length;
  let ctaNeeded = requiredAdds(posts.length, ctaCovered, args.targetCtaCoverage);
  let internalNeeded = requiredAdds(posts.length, internalCovered, args.targetInternalLinkCoverage);
  const changed = [];

  for (const post of posts) {
    if (args.limit !== null && changed.length >= args.limit) break;
    if (post.alreadyEnriched) continue;
    const needsCta = !post.hasCta && ctaNeeded > 0;
    const needsInternalLink = !post.hasInternalLink && internalNeeded > 0;
    if (!needsCta && !needsInternalLink) continue;

    const nextText = `${post.text.trimEnd()}${buildAddition(site, needsCta, needsInternalLink)}`;
    if (!args.dryRun) fs.writeFileSync(post.file, nextText, 'utf8');
    changed.push({
      slug: post.slug,
      file: post.relFile,
      addedCta: needsCta,
      addedInternalLink: needsInternalLink,
    });
    if (needsCta) ctaNeeded -= 1;
    if (needsInternalLink) internalNeeded -= 1;
  }

  return {
    site: siteId,
    totalPosts: posts.length,
    before: {
      ctaCoverage: Number(coverage(posts, 'hasCta').toFixed(3)),
      internalLinkCoverage: Number(coverage(posts, 'hasInternalLink').toFixed(3)),
    },
    requested: {
      targetCtaCoverage: args.targetCtaCoverage,
      targetInternalLinkCoverage: args.targetInternalLinkCoverage,
    },
    changed: changed.length,
    samples: changed.slice(0, 10),
    dryRun: args.dryRun,
  };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const sites = args.sites.split(',').map((site) => site.trim()).filter(Boolean);
  const results = sites.map((siteId) => enrichSite(siteId, args));
  console.log(JSON.stringify({ results }, null, 2));
}

main();
