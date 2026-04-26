#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const REPORT_PATH = path.join(ROOT, 'data', 'sbu-growth', 'control-tower-latest.json');
const TARGET_READY_POSTS = 286;
const MIN_WORDS = 850;

const SITE_CONFIG = {
  finstack: {
    name: 'FinStack',
    category: 'Fintech',
    author: 'FinStack Team',
    cta: 'Explore more fintech infrastructure briefs on FinStack.',
    clusters: [
      'payment reconciliation software',
      'embedded finance platform',
      'banking API provider',
      'invoice automation software',
      'subscription billing platform',
      'revenue recognition workflow',
      'fintech risk monitoring tool',
      'KYC automation platform',
      'open banking data API',
      'treasury management software',
      'card issuing infrastructure',
      'chargeback management software',
      'expense management automation',
      'accounts payable workflow',
      'financial data warehouse',
      'cash flow forecasting tool',
      'fraud detection platform',
      'payment orchestration layer',
    ],
    personas: [
      'SaaS finance teams',
      'marketplace operators',
      'B2B platform teams',
      'startup CFOs',
      'payments product managers',
      'fintech founders',
      'operations leaders',
      'compliance teams',
      'revenue operations teams',
      'banking-as-a-service builders',
    ],
  },
  sellkit: {
    name: 'SellKit',
    category: 'Sales Tools',
    author: 'SellKit Team',
    cta: 'Explore more ecommerce growth stacks on SellKit.',
    clusters: [
      'ecommerce conversion analytics tool',
      'AI product description software',
      'lifecycle email automation platform',
      'customer review mining tool',
      'Shopify conversion rate optimization app',
      'cart recovery automation software',
      'product feed optimization platform',
      'marketplace listing optimization tool',
      'post-purchase upsell software',
      'retention marketing automation',
      'customer segmentation platform',
      'pricing optimization software',
      'affiliate campaign management tool',
      'creator commerce workflow',
      'customer support automation tool',
      'landing page testing software',
      'loyalty program platform',
      'social proof widget',
      'inventory demand forecasting tool',
      'B2B ecommerce sales enablement tool',
    ],
    personas: [
      'ecommerce founders',
      'Shopify teams',
      'DTC operators',
      'growth marketers',
      'marketplace sellers',
      'brand managers',
      'retention teams',
      'revenue operations teams',
      'product marketing teams',
      'customer support leaders',
      'catalog managers',
      'performance marketing teams',
    ],
  },
};

const FRAMES = [
  'buyer checklist',
  'comparison guide',
  'implementation plan',
  'cost model',
  'risk review',
  'migration playbook',
  'vendor evaluation',
  'operating workflow',
  'measurement framework',
  'stack design',
  'automation audit',
  'governance guide',
];

function parseArgs(argv) {
  const args = {
    sites: 'finstack,sellkit',
    report: REPORT_PATH,
    targetReadyPosts: TARGET_READY_POSTS,
    dryRun: false,
    limit: null,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--sites') args.sites = argv[++i] || args.sites;
    else if (arg === '--report') args.report = path.resolve(argv[++i] || REPORT_PATH);
    else if (arg === '--target-ready-posts') args.targetReadyPosts = Number(argv[++i] || TARGET_READY_POSTS);
    else if (arg === '--limit') args.limit = Number(argv[++i] || 0);
    else if (arg === '--dry-run') args.dryRun = true;
  }

  return args;
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function todayKst() {
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
    .slice(0, 110);
}

function titleCase(text) {
  return text
    .split(/\s+/)
    .map((word) => {
      if (/^(AI|API|B2B|B2C|CFO|DTC|KYC|SaaS|CRM|ROAS|SEO)$/i.test(word)) return word.toUpperCase();
      return `${word.slice(0, 1).toUpperCase()}${word.slice(1)}`;
    })
    .join(' ');
}

function yaml(text) {
  return String(text).replace(/"/g, '\\"');
}

function existingSlugs(siteId) {
  const blogDir = path.join(ROOT, 'src', 'sbu', siteId, 'content', 'blog');
  if (!fs.existsSync(blogDir)) return new Set();
  return new Set(fs.readdirSync(blogDir).filter((name) => name.endsWith('.mdx')).map((name) => name.replace(/\.mdx$/, '')));
}

function postWordCount(text) {
  return text
    .replace(/```[\s\S]*?```/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/[^\p{L}\p{N}'-]+/gu, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean).length;
}

function buildPost(site, topic, date, sequence) {
  const clusterTitle = titleCase(topic.cluster);
  const frameTitle = titleCase(topic.frame);
  const personaTitle = topic.persona.replace(/\b\w/g, (letter) => letter.toUpperCase());
  const title = `${clusterTitle} ${frameTitle} for ${personaTitle} in 2026`;
  const keyword = `${topic.cluster} ${topic.frame}`;
  const body = `---\n` +
    `title: "${yaml(title)}"\n` +
    `date: "${date}"\n` +
    `description: "${yaml(`${keyword} - A practical growth and operations guide for ${topic.persona}.`)}"\n` +
    `category: "${yaml(site.category)}"\n` +
    `author: "${yaml(site.author)}"\n` +
    `tags:\n` +
    `  - "${yaml(topic.cluster)}"\n` +
    `  - "${yaml(topic.frame)}"\n` +
    `  - "${yaml(topic.persona)}"\n` +
    `  - "2026"\n` +
    `draft: false\n` +
    `generatedBy: "sbu-gap-expansion-generator"\n` +
    `series: "100k MAU Growth Expansion"\n` +
    `seriesOrder: ${sequence}\n` +
    `---\n\n` +
    `## Executive Snapshot\n\n` +
    `${clusterTitle} decisions matter when ${topic.persona} need repeatable growth without creating a second operations backlog. The goal is not to add another dashboard. The goal is to shorten the path from signal to action while keeping ownership, data quality, and review controls visible.\n\n` +
    `This ${topic.frame} is written for teams that already have a working business process but need a cleaner system for selection, rollout, and measurement. Use it to compare products, define the workflow that should change, and decide whether a specialist tool deserves space in the operating stack.\n\n` +
    `For more related briefs, use the ${site.name} [blog hub](/blog) and compare this guide with the adjacent cluster briefs published for the same buying workflow.\n\n` +
    `## When This Category Is Worth Buying\n\n` +
    `A ${topic.cluster} is worth evaluating when the team sees the same bottleneck every week. That bottleneck can be slow reporting, inconsistent handoffs, fragmented customer data, manual reconciliation, unclear campaign ownership, or weak feedback loops. A tool should remove one of those frictions in a way that can be inspected later.\n\n` +
    `Do not start with the vendor demo. Start with the operating question. What decision should become faster? What manual review should become more reliable? What metric should improve after adoption? If the team cannot answer those questions, the category is not ready for purchase yet.\n\n` +
    `## Selection Criteria\n\n` +
    `### Workflow Fit\n\n` +
    `The strongest choice fits into the current workflow with minimal ceremony. It should connect to the systems that already hold the important data, respect the team's approval path, and make the final owner clear. A broad feature list is less valuable than a product that removes one recurring delay.\n\n` +
    `### Data Quality\n\n` +
    `Useful automation depends on clean inputs. Check how the tool imports records, handles duplicates, exposes errors, and lets operators audit changes. If a tool hides the source of a recommendation, it will be difficult to trust when the decision becomes expensive.\n\n` +
    `### Measurement\n\n` +
    `The tool should connect activity to a business outcome. For ${topic.persona}, the outcome may be conversion, cycle time, revenue leakage, support load, forecast accuracy, retention, or margin. Activity counts are not enough unless they explain a decision that the team will actually make.\n\n` +
    `### Governance\n\n` +
    `Governance is practical, not bureaucratic. Look for permissions, version history, approval status, export paths, and failure alerts. If the tool changes customer-facing output, money movement, compliance state, or a public campaign, it needs a review trail.\n\n` +
    `## Implementation Pattern\n\n` +
    `Begin with one workflow and one metric. Map the current process, identify the owner, and write down the expected improvement before adding the tool. Then run a controlled rollout with a small sample of work. The first milestone should prove that the tool can handle the messy cases, not only the easy demo cases.\n\n` +
    `A practical rollout has four steps. First, define the source of truth and the data fields that matter. Second, connect only the systems needed for the target workflow. Third, route outputs to a human review step. Fourth, compare the before and after metric after enough volume has passed to make the result meaningful.\n\n` +
    `## Operating Metrics\n\n` +
    `Track a short list of metrics so the team can decide whether to expand, pause, or remove the tool. Good metrics include time saved per workflow, number of manual corrections, percent of outputs approved without rework, conversion lift, revenue recovered, incidents avoided, and time from signal to decision.\n\n` +
    `If the metric does not move, look for the reason before blaming the product. The issue may be poor source data, unclear ownership, missing review steps, or a workflow that should not have been automated in the first place.\n\n` +
    `## Risks and Failure Modes\n\n` +
    `The most common failure is buying for volume instead of decision quality. More reports, drafts, segments, alerts, or recommendations are not useful if the team cannot review them and act. Another failure is integration sprawl. A tool that requires too many fragile connections can create more maintenance work than it removes.\n\n` +
    `Vendor lock-in also matters. Confirm export options, API limits, data retention rules, and pricing cliffs before the workflow becomes dependent on the product. A good tool should make the business process more resilient, not harder to leave.\n\n` +
    `## Buying Checklist\n\n` +
    `Use this checklist before shortlisting vendors:\n\n` +
    `- Define the workflow that will change and the owner who approves the change.\n` +
    `- Identify the source systems and the fields required for useful output.\n` +
    `- Choose one success metric and one failure metric.\n` +
    `- Test with real records, not clean demo data.\n` +
    `- Confirm export, permissions, history, alerts, and rollback paths.\n` +
    `- Review the pricing model at the expected usage level, not the starter tier.\n` +
    `- Decide what the team will stop doing if the tool works.\n\n` +
    `## Bottom Line\n\n` +
    `The best ${topic.cluster} for ${topic.persona} is the one that improves a repeated decision and leaves a clear trail. Choose the smallest stack that proves the workflow can become faster, cleaner, or more measurable. Expand only after the operating metric shows that the tool is creating leverage.\n\n` +
    `<InlineCTA\n` +
    `  title="Compare more ${site.name} briefs"\n` +
    `  description="${yaml(site.cta)}"\n` +
    `  buttonText="Explore Blog"\n` +
    `  buttonLink="/blog"\n` +
    `/>\n`;

  const words = postWordCount(body);
  if (words < MIN_WORDS) {
    throw new Error(`Generated post below word target: ${words} words`);
  }

  return { title, body, words };
}

function makeTopics(site, needed, existing) {
  const topics = [];
  let cursor = 0;
  while (topics.length < needed && cursor < needed * 20) {
    const cluster = site.clusters[cursor % site.clusters.length];
    const persona = site.personas[Math.floor(cursor / site.clusters.length) % site.personas.length];
    const frame = FRAMES[Math.floor(cursor / (site.clusters.length * site.personas.length)) % FRAMES.length];
    const baseSlug = slugify(`${cluster}-${frame}-for-${persona}-2026`);
    if (!existing.has(baseSlug)) {
      topics.push({ cluster, persona, frame, slug: baseSlug });
      existing.add(baseSlug);
    }
    cursor += 1;
  }
  return topics;
}

function generateForSite(siteId, args, report, date) {
  const site = SITE_CONFIG[siteId];
  if (!site) throw new Error(`Unsupported site: ${siteId}`);

  const reportSite = report.sites.find((entry) => entry.id === siteId);
  const currentReady = reportSite?.local?.posts?.ready || 0;
  const neededByTarget = Math.max(0, args.targetReadyPosts - currentReady);
  const needed = args.limit === null ? neededByTarget : Math.min(neededByTarget, args.limit);
  const blogDir = path.join(ROOT, 'src', 'sbu', siteId, 'content', 'blog');
  const existing = existingSlugs(siteId);
  const topics = makeTopics(site, needed, existing);
  const created = [];

  if (!args.dryRun) fs.mkdirSync(blogDir, { recursive: true });

  topics.forEach((topic, index) => {
    const slug = `${date}-${topic.slug}`;
    const file = path.join(blogDir, `${slug}.mdx`);
    if (fs.existsSync(file)) return;
    const { title, body, words } = buildPost(site, topic, date, index + 1);
    if (!args.dryRun) fs.writeFileSync(file, body, 'utf8');
    created.push({ slug, title, words, file: path.relative(ROOT, file) });
  });

  return {
    site: siteId,
    currentReady,
    targetReady: args.targetReadyPosts,
    requested: needed,
    created: created.length,
    dryRun: args.dryRun,
    samples: created.slice(0, 5),
  };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const report = readJson(args.report);
  const date = todayKst();
  const sites = args.sites.split(',').map((site) => site.trim()).filter(Boolean);
  const results = sites.map((siteId) => generateForSite(siteId, args, report, date));
  console.log(JSON.stringify({ date, targetReadyPosts: args.targetReadyPosts, results }, null, 2));
}

main();
