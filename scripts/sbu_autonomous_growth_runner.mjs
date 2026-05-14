#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const NPM = process.platform === 'win32' ? 'npm.cmd' : 'npm';
const NPX = process.platform === 'win32' ? 'npx.cmd' : 'npx';

const SITES = [
  {
    id: 'aiforge',
    name: 'AIForge',
    domain: 'https://aiforge.neogenesis.app',
    repo: 'Yesol-Pilot/aiforge',
    author: 'AIForge Team',
    category: 'AI Tools',
    niche: 'AI tools, agent platforms, model operations, and workflow automation',
    cta: 'Explore curated AI tool stacks on AIForge.',
    topics: [
      ['ai-agent-evaluation-platforms', 'AI Agent Evaluation Platforms for Product Teams', 'AI agent evaluation platforms'],
      ['llm-observability-tools', 'LLM Observability Tools for Lean AI Teams', 'LLM observability tools'],
      ['ai-workflow-automation-stack', 'AI Workflow Automation Stack for Small Teams', 'AI workflow automation stack'],
      ['agentic-crm-automation-tools', 'Agentic CRM Automation Tools for Growth Teams', 'agentic CRM automation tools'],
    ],
  },
  {
    id: 'craftdesk',
    name: 'CraftDesk',
    domain: 'https://craftdesk.neogenesis.app',
    repo: 'Yesol-Pilot/craftdesk',
    author: 'CraftDesk Team',
    category: 'Design Tools',
    niche: 'design tools, creative automation, UI systems, and product design workflows',
    cta: 'Explore practical software stacks for design and creative teams.',
    topics: [
      ['ai-design-qa-tools', 'AI Design QA Tools for Product Teams', 'AI design QA tools'],
      ['creative-automation-workflow-tools', 'Creative Automation Workflow Tools for Small Teams', 'creative automation workflow tools'],
      ['design-system-documentation-tools', 'Design System Documentation Tools for 2026', 'design system documentation tools'],
      ['brand-asset-workflow-software', 'Brand Asset Workflow Software for Marketing Teams', 'brand asset workflow software'],
    ],
  },
  {
    id: 'deploystack',
    name: 'DeployStack',
    domain: 'https://deploystack.neogenesis.app',
    repo: 'Yesol-Pilot/deploystack',
    author: 'DeployStack Team',
    category: 'DevOps',
    niche: 'deployment platforms, serverless infrastructure, observability, and DevOps workflows',
    cta: 'Explore deployment stacks on DeployStack.',
    topics: [
      ['deployment-preview-workflows', 'Deployment Preview Workflows for Startup Teams', 'deployment preview workflows'],
      ['serverless-cost-monitoring-tools', 'Serverless Cost Monitoring Tools for 2026', 'serverless cost monitoring tools'],
      ['edge-deployment-platforms', 'Edge Deployment Platforms for Product Teams', 'edge deployment platforms'],
      ['devops-incident-review-tools', 'DevOps Incident Review Tools for Small Teams', 'DevOps incident review tools'],
    ],
  },
  {
    id: 'finstack',
    name: 'FinStack',
    domain: 'https://finstack.neogenesis.app',
    repo: 'Yesol-Pilot/finstack',
    author: 'FinStack Team',
    category: 'Fintech',
    niche: 'fintech infrastructure, payments, banking workflows, and financial SaaS tools',
    cta: 'Explore curated fintech stacks on FinStack.',
    topics: [
      ['payment-reconciliation-tools', 'Payment Reconciliation Tools for SaaS Finance Teams', 'payment reconciliation tools'],
      ['fintech-risk-monitoring-platforms', 'Fintech Risk Monitoring Platforms for 2026', 'fintech risk monitoring platforms'],
      ['invoice-automation-software', 'Invoice Automation Software for Lean Finance Teams', 'invoice automation software'],
      ['banking-api-platforms', 'Banking API Platforms for SaaS Builders', 'banking API platforms'],
    ],
  },
  {
    id: 'sellkit',
    name: 'SellKit',
    domain: 'https://sellkit.neogenesis.app',
    repo: 'Yesol-Pilot/sellkit',
    author: 'SellKit Team',
    category: 'Sales Tools',
    niche: 'ecommerce growth, sales enablement, marketing automation, and conversion tools',
    cta: 'Explore ecommerce growth stacks on SellKit.',
    topics: [
      ['ecommerce-conversion-analytics-tools', 'Ecommerce Conversion Analytics Tools for 2026', 'ecommerce conversion analytics tools'],
      ['ai-product-description-tools', 'AI Product Description Tools for Online Stores', 'AI product description tools'],
      ['customer-review-mining-tools', 'Customer Review Mining Tools for Ecommerce Teams', 'customer review mining tools'],
      ['lifecycle-email-automation-tools', 'Lifecycle Email Automation Tools for Lean Ecommerce Teams', 'lifecycle email automation tools'],
    ],
  },
];

function parseArgs(argv) {
  const args = {
    sites: 'all',
    dryRun: false,
    force: false,
    skipBuild: false,
    skipDeploy: false,
    verifyOnly: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--sites') args.sites = argv[++i] || 'all';
    else if (arg === '--dry-run') args.dryRun = true;
    else if (arg === '--force') args.force = true;
    else if (arg === '--skip-build') args.skipBuild = true;
    else if (arg === '--skip-deploy') args.skipDeploy = true;
    else if (arg === '--verify-only') args.verifyOnly = true;
  }
  return args;
}

function run(cmd, args, cwd, options = {}) {
  const needsShell = process.platform === 'win32' && (cmd.endsWith('.cmd') || cmd.endsWith('.bat'));
  const result = spawnSync(cmd, args, {
    cwd,
    encoding: 'utf8',
    shell: needsShell,
    stdio: options.capture ? ['ignore', 'pipe', 'pipe'] : 'inherit',
  });
  if (result.status !== 0) {
    const detail = options.capture ? `${result.stdout || ''}${result.stderr || ''}`.trim() : '';
    throw new Error(`${cmd} ${args.join(' ')} failed${detail ? `: ${detail}` : ''}`);
  }
  return options.capture ? (result.stdout || '').trim() : '';
}

function isGitIgnored(cwd, relativeFile) {
  const result = spawnSync('git', ['check-ignore', '-q', relativeFile], {
    cwd,
    encoding: 'utf8',
    shell: false,
    stdio: 'ignore',
  });
  if (result.status === 0) return true;
  if (result.status === 1) return false;
  const message = result.error ? result.error.message : 'unknown error';
  throw new Error(`git check-ignore failed for ${relativeFile}: ${message}`);
}

function kstDate() {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Seoul',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(new Date());
  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${values.year}-${values.month}-${values.day}`;
}

function slugify(text) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .slice(0, 90);
}

function yaml(text) {
  return String(text).replace(/"/g, '\\"');
}

function frontmatterDate(file) {
  const text = fs.readFileSync(file, 'utf8');
  const match = text.match(/^date:\s*["']?([^"'\r\n]+)["']?/m);
  return match ? match[1].trim() : '';
}

function frontmatterTitle(file) {
  const text = fs.readFileSync(file, 'utf8');
  const match = text.match(/^title:\s*["']?([^"'\r\n]+)["']?/m);
  return match ? match[1].trim() : '';
}

function latestPost(siteDir) {
  const blogDir = path.join(siteDir, 'content', 'blog');
  if (!fs.existsSync(blogDir)) return null;
  const posts = fs
    .readdirSync(blogDir)
    .filter((name) => name.endsWith('.mdx'))
    .map((name) => {
      const file = path.join(blogDir, name);
      return {
        slug: name.replace(/\.mdx$/, ''),
        date: frontmatterDate(file),
        title: frontmatterTitle(file),
      };
    })
    .filter((post) => post.date)
    .sort((a, b) => b.date.localeCompare(a.date));
  return posts[0] || null;
}

function selectTopic(site, date) {
  const dayNumber = Number(date.replace(/-/g, ''));
  const [slug, title, keyword] = site.topics[dayNumber % site.topics.length];
  return { slug, title, keyword };
}

function buildArticle(site, topic, date) {
  const year = date.slice(0, 4);
  const title = `${topic.title} in ${year}`;
  return `---
title: "${yaml(title)}"
date: "${date}"
description: "${yaml(`${topic.keyword} - A practical evaluation guide for ${site.niche}.`)}"
category: "${yaml(site.category)}"
author: "${yaml(site.author)}"
tags:
  - "${yaml(topic.keyword)}"
  - "${yaml(site.id)}"
  - "workflow"
  - "${year}"
draft: false
generatedBy: "sbu-autonomous-growth-runner"
---

## The Shortlist

${topic.keyword} matter because small teams need operating leverage without adding avoidable process debt. The strongest tools in this category help teams make decisions faster, preserve context, and reduce repeated manual work.

For ${site.name}, the useful buying question is not whether a product has an impressive demo. The useful question is whether it improves a repeatable workflow in ${site.niche}.

## What Changed in ${year}

Software buyers are more selective now. Teams want automation, but they also want clear ownership, lower switching cost, better reporting, and fewer fragile integrations. A tool that saves time in one step but creates review, support, or data cleanup work later is not a strong choice.

The best products now combine four traits:

- They connect to the systems the team already uses.
- They make review and approval visible.
- They expose enough data to measure whether the workflow improved.
- They avoid locking critical knowledge inside a black box.

## Evaluation Criteria

### Workflow Fit

Start with the workflow that wastes the most time. Define the before and after state before comparing vendors. A narrower tool that removes one persistent bottleneck is usually better than a broad platform that adds another dashboard.

The clearest signal is adoption by the person who owns the work every week. If the tool is only used during a launch, audit, or one-off cleanup, it should be evaluated as a project tool rather than a core operating system. If it becomes the default surface for planning, review, and measurement, it can justify deeper integration.

### Governance

Governance is not only a large-company concern. Small teams also need version history, permissions, approval paths, and clear ownership. When a tool affects customer-facing work, pricing, money movement, production systems, or brand promises, review controls matter.

Good governance should be visible without slowing the team down. Look for practical controls: who can change settings, who can approve output, which data is retained, and how rollback works when a workflow creates the wrong result. If the product cannot explain these controls clearly, the team will carry hidden operational risk.

### Data and Reporting

Useful reporting connects the tool's output to business results. Look for evidence that the product can track adoption, throughput, conversion, reliability, cost, or quality. If reporting stops at activity counts, the team may not know whether the tool is working.

Reporting should also expose failure. Strong tools make it easy to see skipped tasks, stale data, failed syncs, and delayed approvals. This matters because automation failure is often silent. A daily or weekly review surface is more valuable than a glossy dashboard that only shows successful activity.

### Integration Cost

Every integration creates maintenance work. Prioritize tools with stable APIs, clear exports, webhook reliability, and clean fallback paths. A tool should make the core workflow simpler, not more fragile.

The practical test is a one-day outage. If the integration fails for a day, the team should still know what work is blocked, what can continue manually, and what data must be reconciled afterward. Products that provide exports, audit logs, and predictable retries are safer choices for small teams.

## Implementation Playbook

Use a short pilot before changing the whole operating model. Pick one team, one workflow, one metric, and one failure mode to watch. Write down the baseline before the pilot starts, then compare the result after the same volume of work has passed through the new process.

A useful pilot includes:

- One owner who can decide whether the tool stays or goes.
- One repeated workflow that happens at least weekly.
- One measurable output such as cycle time, cost per task, lead quality, defect rate, or review time.
- One rollback path if the tool creates extra work.

Avoid pilots that only measure enthusiasm. A team can like a tool and still fail to use it when real deadlines arrive. The better signal is whether the tool survives a busy week without creating support load.

## Recommended Stack Pattern

Start with one primary system of record, one automation layer, and one reporting surface. Add specialized tools only after the team can explain what decision each tool improves.

For early teams, the default pattern should be:

- One source of truth for the workflow.
- One automation step that removes repeated manual work.
- One review step before high-impact output goes live.
- One metric that proves the workflow improved.

## Common Failure Modes

The most common mistake is buying a tool for output volume. More output is not useful when the team cannot review it, route it, measure it, or maintain it.

Another failure mode is ignoring the handoff. A tool can create a strong draft, report, or recommendation, but the business value appears only when the next owner can act on it without rebuilding the context.

The third failure mode is tool sprawl. Teams add a specialized product for every pain point, then lose the ability to understand where the source of truth lives. If a new product does not replace a manual step, reduce review time, or improve a decision, it is probably adding surface area rather than leverage.

## Metrics to Track

Track a small number of metrics that connect directly to operating quality:

- Time from request to reviewed output.
- Number of manual handoffs per workflow.
- Percentage of work that needs rework after review.
- Cost per completed workflow.
- Adoption by the workflow owner after the pilot period.
- Number of incidents, failed syncs, or stale records.

These metrics are intentionally simple. The point is not to build a perfect attribution model. The point is to know whether the tool made the workflow more reliable and whether the team can keep using it without creating another maintenance burden.

## Buying Checklist

Before adopting a ${topic.keyword} product, answer these questions:

- What workflow will this replace or improve?
- Who owns review and approval?
- What data does the tool need, and where will that data live?
- Can we export the work if we leave the product?
- What metric will show that the workflow improved?
- What breaks if the integration fails for a day?

## Bottom Line

The best ${topic.keyword} for ${year} are not the tools that create the most artifacts. They are the tools that make a repeated workflow more reliable. Choose the product that shortens the path from signal to decision, then keep the stack simple until the volume justifies more automation.

<InlineCTA
  title="Need more tool comparisons?"
  description="${yaml(site.cta)}"
  buttonText="Explore Stacks"
  buttonLink="/stacks/solo-startup"
/>
`;
}

async function fetchText(url) {
  const response = await fetch(url, { redirect: 'follow' });
  const text = await response.text();
  return { status: response.status, text };
}

async function verifyLive(site, slug, title, date) {
  const blog = await fetchText(`${site.domain}/blog`);
  const detail = await fetchText(`${site.domain}/blog/${slug}`);
  const sitemap = await fetchText(`${site.domain}/sitemap.xml`);
  return {
    blog: blog.status === 200 && blog.text.includes(date) && blog.text.includes(slug),
    detail: detail.status === 200 && detail.text.includes(title) && detail.text.includes(date),
    sitemap: sitemap.status === 200 && sitemap.text.includes(`/blog/${slug}`),
  };
}

function ensureCleanEnough(siteDir) {
  const status = run('git', ['status', '--short'], siteDir, { capture: true });
  if (status) {
    throw new Error(`working tree is not clean: ${status.replace(/\n/g, '; ')}`);
  }
}

async function processSite(site, args, date) {
  const siteDir = path.join(ROOT, 'src', 'sbu', site.id);
  const topic = selectTopic(site, date);
  const slug = `${date}-${topic.slug}`;
  const title = `${topic.title} in ${date.slice(0, 4)}`;
  const filePath = path.join(siteDir, 'content', 'blog', `${slug}.mdx`);

  if (args.verifyOnly) {
    const latest = latestPost(siteDir);
    if (!latest) throw new Error(`${site.id} has no MDX posts to verify`);
    const live = await verifyLive(site, latest.slug, latest.title, latest.date);
    return { site: site.id, action: 'verify-only', slug: latest.slug, latest: latest.date, live };
  }

  const latest = latestPost(siteDir);
  if (!args.force && latest?.date >= date) {
    return { site: site.id, action: 'skip-fresh', latest: latest.date, slug: latest.slug };
  }

  const remote = run('git', ['remote', '-v'], siteDir, { capture: true });
  if (!remote.includes(site.repo)) {
    throw new Error(`${site.id} remote mismatch. Expected ${site.repo}`);
  }

  const email = run('git', ['config', 'user.email'], siteDir, { capture: true });
  if (email !== 'dpthf1537@gmail.com') {
    throw new Error(`${site.id} git user.email mismatch: ${email}`);
  }

  ensureCleanEnough(siteDir);

  if (args.dryRun) {
    return { site: site.id, action: 'dry-run-create', slug, file: path.relative(ROOT, filePath) };
  }

  if (!fs.existsSync(filePath)) {
    fs.writeFileSync(filePath, buildArticle(site, topic, date), 'utf8');
  }

  if (!args.skipBuild) {
    run(NPM, ['run', 'build'], siteDir);
  }

  const addTargets = [path.relative(siteDir, filePath)];
  const llms = path.join(siteDir, 'public', 'llms.txt');
  if (fs.existsSync(llms)) {
    const rel = path.relative(siteDir, llms);
    if (!isGitIgnored(siteDir, rel)) addTargets.push(rel);
  }

  run('git', ['add', ...addTargets], siteDir);
  const staged = run('git', ['diff', '--cached', '--name-only'], siteDir, { capture: true });
  if (staged) {
    run('git', ['commit', '-m', `content: publish ${site.name} autonomous post ${date}`], siteDir);
    run('git', ['push', 'origin', 'main'], siteDir);
  }

  let deployment = 'skipped';
  if (!args.skipDeploy) {
    run(NPX, ['vercel', '--prod', '--yes', '--scope', 'yesol-pilots-projects'], siteDir);
    deployment = 'completed';
  }

  const live = await verifyLive(site, slug, title, date);
  if (!live.blog || !live.detail || !live.sitemap) {
    throw new Error(`${site.id} live verification failed: ${JSON.stringify(live)}`);
  }

  return { site: site.id, action: staged ? 'published' : 'already-existed', slug, deployment, live };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const requested = args.sites === 'all'
    ? SITES
    : SITES.filter((site) => args.sites.split(',').map((s) => s.trim()).includes(site.id));
  const date = kstDate();
  const results = [];

  for (const site of requested) {
    try {
      results.push(await processSite(site, args, date));
    } catch (error) {
      results.push({ site: site.id, action: 'failed', error: error instanceof Error ? error.message : String(error) });
    }
  }

  console.log(JSON.stringify({ date, results }, null, 2));
  if (results.some((result) => result.action === 'failed')) process.exit(1);
}

main();
