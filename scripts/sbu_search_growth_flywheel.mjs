#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { createHash, createSign } from 'node:crypto';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT_DIR = path.join(ROOT, 'data', 'sbu-growth');
const DEFAULT_SITES =
  'toolpick,aiforge,craftdesk,deploystack,finstack,sellkit,reviewlab,ur-wrong,kott,ethicaai,whylab,portfolio,neogenesis';
const CORE_SITES = ['toolpick', 'aiforge', 'craftdesk', 'deploystack', 'finstack', 'sellkit'];
const MARKER = 'sbu-search-growth-flywheel';

const SITES = {
  toolpick: {
    name: 'ToolPick',
    siteUrl: 'https://www.toolpick.dev/',
    domain: 'https://www.toolpick.dev',
    localDir: path.join(ROOT, 'src', 'sbu', 'toolpick'),
  },
  aiforge: {
    name: 'AIForge',
    siteUrl: 'https://aiforge.neogenesis.app/',
    domain: 'https://aiforge.neogenesis.app',
    localDir: path.join(ROOT, 'src', 'sbu', 'aiforge'),
  },
  craftdesk: {
    name: 'CraftDesk',
    siteUrl: 'https://craftdesk.neogenesis.app/',
    domain: 'https://craftdesk.neogenesis.app',
    localDir: path.join(ROOT, 'src', 'sbu', 'craftdesk'),
  },
  deploystack: {
    name: 'DeployStack',
    siteUrl: 'https://deploystack.neogenesis.app/',
    domain: 'https://deploystack.neogenesis.app',
    localDir: path.join(ROOT, 'src', 'sbu', 'deploystack'),
  },
  finstack: {
    name: 'FinStack',
    siteUrl: 'https://finstack.neogenesis.app/',
    domain: 'https://finstack.neogenesis.app',
    localDir: path.join(ROOT, 'src', 'sbu', 'finstack'),
  },
  sellkit: {
    name: 'SellKit',
    siteUrl: 'https://sellkit.neogenesis.app/',
    domain: 'https://sellkit.neogenesis.app',
    localDir: path.join(ROOT, 'src', 'sbu', 'sellkit'),
  },
  reviewlab: {
    name: 'ReviewLab',
    siteUrl: 'https://review.neogenesis.app/',
    domain: 'https://review.neogenesis.app',
    localDir: path.join(ROOT, 'src', 'sbu', 'reviewlab'),
  },
  'ur-wrong': {
    name: 'UR WRONG',
    siteUrl: 'https://ur-wrong.com/',
    domain: 'https://ur-wrong.com',
    localDir: path.join(ROOT, 'src', 'sbu', 'ur-wrong'),
  },
  kott: {
    name: 'K-OTT',
    siteUrl: 'https://kott.kr/',
    domain: 'https://kott.kr',
    localDir: path.join(ROOT, 'src', 'sbu', 'k-ott', 'frontend'),
  },
  ethicaai: {
    name: 'EthicaAI',
    siteUrl: 'https://ethica.neogenesis.app/',
    domain: 'https://ethica.neogenesis.app',
    localDir: path.join(ROOT, 'src', 'sbu', 'ethicaai', 'site'),
  },
  whylab: {
    name: 'WhyLab',
    siteUrl: 'https://whylab.neogenesis.app/',
    domain: 'https://whylab.neogenesis.app',
    localDir: path.join(ROOT, '..', 'github_repos', 'WhyLab', 'dashboard'),
  },
  portfolio: {
    name: 'Portfolio',
    siteUrl: 'https://heoyesol.kr/',
    domain: 'https://heoyesol.kr',
    localDir: path.join(ROOT, '..', 'portfolio'),
  },
  neogenesis: {
    name: 'NeoGenesis',
    siteUrl: 'https://neogenesis.app/',
    domain: 'https://neogenesis.app',
    localDir: path.join(ROOT, 'src', 'landing'),
  },
};

const REQUIRED_POSTHOG_EVENTS = ['scroll_depth', 'cta_viewport_reached', 'cta_click', 'affiliate_click'];
const RECOMMENDED_POSTHOG_EVENTS = [
  '$pageview',
  'ai_search_visit',
  'return_visit',
  'outbound_official_click',
  'topic_hub_click',
  'signup_intent',
];

function parseArgs(argv) {
  const args = {
    sites: DEFAULT_SITES,
    days: 28,
    rowLimit: 1000,
    minImpressions: 3,
    applyContent: false,
    maxApplyPerSite: 3,
    maxStaleDays: 2,
    json: false,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--sites') args.sites = argv[++i] || args.sites;
    else if (arg === '--core-only') args.sites = CORE_SITES.join(',');
    else if (arg === '--days') args.days = Number(argv[++i] || args.days);
    else if (arg === '--row-limit') args.rowLimit = Number(argv[++i] || args.rowLimit);
    else if (arg === '--min-impressions') args.minImpressions = Number(argv[++i] || args.minImpressions);
    else if (arg === '--apply-content') args.applyContent = true;
    else if (arg === '--max-apply-per-site') args.maxApplyPerSite = Number(argv[++i] || args.maxApplyPerSite);
    else if (arg === '--max-stale-days') args.maxStaleDays = Number(argv[++i] || args.maxStaleDays);
    else if (arg === '--json') args.json = true;
  }

  return args;
}

function nowKst() {
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

function kstDateOffset(days) {
  const now = new Date();
  const kst = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  kst.setDate(kst.getDate() + days);
  const year = kst.getFullYear();
  const month = String(kst.getMonth() + 1).padStart(2, '0');
  const day = String(kst.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function dateRange(days) {
  const endDate = kstDateOffset(-2);
  const start = new Date(`${endDate}T00:00:00+09:00`);
  start.setDate(start.getDate() - Math.max(1, days) + 1);
  return { startDate: start.toISOString().slice(0, 10), endDate };
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function readEnvFiles() {
  const env = {};
  for (const file of [path.join(ROOT, '.env.local'), path.join(ROOT, '.env')]) {
    if (!fs.existsSync(file)) continue;
    const text = fs.readFileSync(file, 'utf8');
    for (const line of text.split(/\r?\n/)) {
      if (!line.trim() || line.trim().startsWith('#')) continue;
      const index = line.indexOf('=');
      if (index < 0) continue;
      const key = line.slice(0, index).trim();
      let value = line.slice(index + 1).trim();
      value = value.replace(/^"(.*)"$/, '$1').replace(/^'(.*)'$/, '$1');
      if (key && value) env[key] = value;
    }
  }
  return env;
}

const SERVICE_ACCOUNT_KEYS = [
  'GSC_SERVICE_ACCOUNT_JSON',
  'GOOGLE_SERVICE_ACCOUNT_JSON',
  'GA4_SERVICE_ACCOUNT_PATH',
  'GOOGLE_APPLICATION_CREDENTIALS',
];

function loadServiceAccount(rawValue) {
  const trimmed = String(rawValue || '').trim();
  if (!trimmed) return { ok: false, error: 'empty_value' };

  try {
    if (trimmed.startsWith('{')) return { ok: true, credentials: JSON.parse(trimmed), type: 'json' };

    const candidates = [
      path.isAbsolute(trimmed) ? trimmed : path.resolve(ROOT, trimmed),
      path.resolve(trimmed),
    ];
    const file = [...new Set(candidates)].find((candidate) => fs.existsSync(candidate));
    if (!file) return { ok: false, error: 'file_not_found' };
    return { ok: true, credentials: JSON.parse(fs.readFileSync(file, 'utf8')), type: 'file' };
  } catch {
    return { ok: false, error: 'parse_failed' };
  }
}

function discoverServiceAccounts() {
  const envFile = readEnvFiles();
  const rawCandidates = [];

  for (const key of SERVICE_ACCOUNT_KEYS) {
    if (process.env[key]) rawCandidates.push({ key, origin: 'process.env', value: process.env[key] });
    if (envFile[key]) rawCandidates.push({ key, origin: 'env-file', value: envFile[key] });
  }

  const seen = new Set();
  const candidates = [];
  for (const raw of rawCandidates) {
    const label = `${raw.key}@${raw.origin}`;
    const loaded = loadServiceAccount(raw.value);
    if (!loaded.ok) {
      candidates.push({ ok: false, label, key: raw.key, origin: raw.origin, error: loaded.error });
      continue;
    }

    const credentials = loaded.credentials || {};
    const fingerprint = safeHash(`${credentials.client_email || ''}:${credentials.private_key_id || ''}:${credentials.project_id || ''}`);
    const dedupeKey = `${fingerprint}:${credentials.client_email ? 'email' : 'missing_email'}`;
    if (seen.has(dedupeKey)) continue;
    seen.add(dedupeKey);
    candidates.push({
      ok: true,
      label,
      key: raw.key,
      origin: raw.origin,
      type: loaded.type,
      accountHash: fingerprint,
      credentials,
    });
  }

  return candidates;
}

async function getAccessTokenForCredentials(credentials, scopes) {
  if (!credentials?.client_email || !credentials?.private_key) {
    return { ok: false, error: 'service_account_missing' };
  }

  const now = Math.floor(Date.now() / 1000);
  const payload = {
    iss: credentials.client_email,
    scope: scopes.join(' '),
    aud: 'https://oauth2.googleapis.com/token',
    iat: now,
    exp: now + 3600,
  };
  const header = { alg: 'RS256', typ: 'JWT' };
  const encodedHeader = Buffer.from(JSON.stringify(header)).toString('base64url');
  const encodedPayload = Buffer.from(JSON.stringify(payload)).toString('base64url');
  const signer = createSign('RSA-SHA256');
  signer.update(`${encodedHeader}.${encodedPayload}`);
  const signature = signer.sign(credentials.private_key, 'base64url');
  const assertion = `${encodedHeader}.${encodedPayload}.${signature}`;

  const response = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
      assertion,
    }),
  });
  const text = await response.text();
  if (!response.ok) return { ok: false, status: response.status, error: text.slice(0, 240) };
  return { ok: true, token: JSON.parse(text).access_token };
}

async function getSearchConsoleToken(scopes) {
  const candidates = discoverServiceAccounts();
  const attempts = [];
  if (!candidates.length) return { ok: false, error: 'service_account_missing', attempts };

  for (const candidate of candidates) {
    const attempt = {
      source: candidate.label,
      accountHash: candidate.accountHash || null,
      stage: 'load',
      ok: false,
      status: null,
      siteCount: 0,
    };

    if (!candidate.ok) {
      attempt.error = candidate.error;
      attempts.push(attempt);
      continue;
    }

    const tokenResult = await getAccessTokenForCredentials(candidate.credentials, scopes);
    if (!tokenResult.ok) {
      attempts.push({
        ...attempt,
        stage: 'oauth',
        status: tokenResult.status || null,
        error: 'oauth_failed',
      });
      continue;
    }

    const headers = { authorization: `Bearer ${tokenResult.token}`, 'content-type': 'application/json' };
    const listResponse = await fetchJson('https://www.googleapis.com/webmasters/v3/sites', { headers }, 1);
    const siteCount = Array.isArray(listResponse.json?.siteEntry) ? listResponse.json.siteEntry.length : 0;
    const ok = listResponse.ok && Array.isArray(listResponse.json?.siteEntry);
    attempts.push({
      ...attempt,
      stage: 'sites.list',
      ok,
      status: listResponse.status,
      siteCount,
      error: ok ? null : `sites_list_${listResponse.status || 'failed'}`,
    });

    if (ok) {
      return {
        ok: true,
        token: tokenResult.token,
        listResponse,
        credential: {
          source: candidate.label,
          accountHash: candidate.accountHash,
        },
        attempts,
      };
    }
  }

  return { ok: false, error: 'search_console_credential_failed', attempts };
}

async function fetchJson(url, options = {}, retries = 3) {
  for (let attempt = 0; attempt <= retries; attempt += 1) {
    const response = await fetch(url, {
      ...options,
      headers: {
        'user-agent': 'neo-sbu-search-growth-flywheel/1.0',
        ...(options.headers || {}),
      },
    });
    const text = await response.text();
    let json = null;
    try {
      json = text ? JSON.parse(text) : null;
    } catch {}

    if (response.ok) return { ok: true, status: response.status, json, text };
    if (![429, 500, 502, 503, 504].includes(response.status) || attempt === retries) {
      return { ok: false, status: response.status, json, text: text.slice(0, 400) };
    }
    await sleep(1500 * (attempt + 1));
  }
  return { ok: false, status: 0, text: 'retry_exhausted' };
}

async function fetchText(url) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(url, {
      redirect: 'follow',
      signal: controller.signal,
      headers: { 'user-agent': 'neo-sbu-search-growth-flywheel/1.0' },
    });
    return { ok: response.ok, status: response.status, text: await response.text(), url: response.url };
  } catch (error) {
    return { ok: false, status: 0, text: '', error: String(error?.message || error) };
  } finally {
    clearTimeout(timer);
  }
}

function safeHash(value) {
  return createHash('sha1').update(value).digest('hex').slice(0, 12);
}

function sanitizeText(value, fallback = '') {
  return String(value || fallback)
    .replace(/[\r\n]+/g, ' ')
    .replace(/[<>]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function slugFromPage(page) {
  try {
    const pathname = new URL(page).pathname.replace(/\/$/, '');
    const match = pathname.match(/^\/blog\/([^/]+)$/);
    return match ? decodeURIComponent(match[1]) : '';
  } catch {
    return '';
  }
}

function localBlogFile(site, page) {
  if (!site.localDir) return null;
  const slug = slugFromPage(page);
  if (!slug) return null;
  const candidates = [
    path.join(site.localDir, 'content', 'blog', `${slug}.mdx`),
    path.join(site.localDir, 'src', 'content', 'blog', `${slug}.mdx`),
  ];
  return candidates.find((candidate) => fs.existsSync(candidate)) || null;
}

function classifyOpportunity(row, args) {
  const impressions = Number(row.impressions || 0);
  const clicks = Number(row.clicks || 0);
  const ctr = Number(row.ctr || 0);
  const position = Number(row.position || 0);
  if (impressions < args.minImpressions) return null;

  let action = 'monitor';
  if (position > 0 && position <= 12 && ctr <= 0.02) action = 'rewrite_title_meta';
  else if (position >= 8 && position <= 20) action = 'expand_striking_distance';
  else if (position > 20) action = 'add_depth_and_internal_links';
  else if (clicks > 0 && position <= 8) action = 'reinforce_winner';

  const ctrGap = Math.max(0, 0.05 - ctr);
  const positionWeight = position > 0 ? 1 / Math.sqrt(position) : 0.1;
  const actionBoost = {
    rewrite_title_meta: 4,
    expand_striking_distance: 3,
    add_depth_and_internal_links: 2,
    reinforce_winner: 1.5,
    monitor: 0.5,
  }[action];
  const score = Number((impressions * (ctrGap + 0.01) * positionWeight * actionBoost).toFixed(4));

  return { action, score };
}

async function collectGsc(token, siteIds, args, listResponse = null, credential = null, credentialAttempts = []) {
  const { startDate, endDate } = dateRange(args.days);
  const headers = { authorization: `Bearer ${token}`, 'content-type': 'application/json' };
  const verifiedListResponse = listResponse || await fetchJson('https://www.googleapis.com/webmasters/v3/sites', { headers });
  const listed = new Map(
    (verifiedListResponse.json?.siteEntry || []).map((entry) => [entry.siteUrl, entry.permissionLevel]),
  );
  const siteReports = [];

  for (const siteId of siteIds) {
    const site = SITES[siteId];
    const encodedSite = encodeURIComponent(site.siteUrl);
    const sitemapUrl = `${site.siteUrl.replace(/\/$/, '')}/sitemap.xml`;
    const sitemapEndpoint = `https://www.googleapis.com/webmasters/v3/sites/${encodedSite}/sitemaps/${encodeURIComponent(sitemapUrl)}`;
    const sitemapResponse = await fetchJson(sitemapEndpoint, { headers }, 2);
    await sleep(850);

    const body = {
      startDate,
      endDate,
      dimensions: ['query', 'page'],
      rowLimit: args.rowLimit,
    };
    const queryResponse = await fetchJson(
      `https://www.googleapis.com/webmasters/v3/sites/${encodedSite}/searchAnalytics/query`,
      { method: 'POST', headers, body: JSON.stringify(body) },
      3,
    );
    await sleep(850);

    const rows = (queryResponse.json?.rows || []).map((row) => {
      const [query, page] = row.keys || ['', ''];
      const localFile = localBlogFile(site, page);
      const opportunity = classifyOpportunity(row, args);
      return {
        query,
        page,
        clicks: Number(row.clicks || 0),
        impressions: Number(row.impressions || 0),
        ctr: Number(Number(row.ctr || 0).toFixed(4)),
        position: Number(Number(row.position || 0).toFixed(2)),
        localFile: localFile ? path.relative(ROOT, localFile) : null,
        localEditable: Boolean(localFile),
        action: opportunity?.action || 'ignore_low_signal',
        score: opportunity?.score || 0,
      };
    });

    const opportunities = rows
      .filter((row) => row.score > 0 && row.action !== 'monitor')
      .sort((a, b) => b.score - a.score)
      .slice(0, 50);

    siteReports.push({
      site: siteId,
      name: site.name,
      siteUrl: site.siteUrl,
      permission: listed.get(site.siteUrl) || null,
      propertyListed: listed.has(site.siteUrl),
      sitemapKnown: sitemapResponse.status === 200,
      searchAnalytics: {
        status: queryResponse.status,
        ok: queryResponse.ok,
        rowCount: rows.length,
        startDate,
        endDate,
        noDataYet: queryResponse.ok && rows.length === 0,
      },
      topRows: rows
        .sort((a, b) => b.impressions - a.impressions || b.clicks - a.clicks)
        .slice(0, 25),
      opportunities,
    });
  }

  return {
    startDate,
    endDate,
    credential,
    credentialAttempts,
    sites: siteReports,
    propertyListedOk: siteReports.filter((site) => site.propertyListed).length,
    sitemapKnownOk: siteReports.filter((site) => site.sitemapKnown).length,
    opportunityCount: siteReports.reduce((sum, site) => sum + site.opportunities.length, 0),
  };
}

function gitStatus(cwd) {
  const result = spawnSync('git', ['status', '--porcelain'], {
    cwd,
    encoding: 'utf8',
    shell: false,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  if (result.status !== 0) return { ok: false, dirty: true, text: (result.stderr || '').trim() };
  const text = (result.stdout || '').trim();
  return { ok: true, dirty: text.length > 0, text };
}

function parseFrontmatter(text) {
  const match = text.replace(/^\uFEFF/, '').match(/^---\s*\r?\n([\s\S]*?)\r?\n---\s*/);
  if (!match) return { block: '', body: text, frontmatter: {} };
  const frontmatter = {};
  for (const line of match[1].split(/\r?\n/)) {
    const pair = line.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
    if (!pair) continue;
    frontmatter[pair[1]] = pair[2].trim().replace(/^['"]|['"]$/g, '');
  }
  return { block: match[1], body: text.slice(match[0].length), frontmatter };
}

function updateFrontmatter(text, updates) {
  const clean = text.replace(/^\uFEFF/, '');
  const match = clean.match(/^---\s*\r?\n([\s\S]*?)\r?\n---\s*/);
  if (!match) return text;
  let lines = match[1].split(/\r?\n/);
  for (const [key, value] of Object.entries(updates)) {
    const nextLine = `${key}: "${String(value).replace(/"/g, '\\"')}"`;
    const nextLines = [];
    let replaced = false;
    for (let i = 0; i < lines.length; i += 1) {
      const current = lines[i];
      const matchKey = current.match(/^([A-Za-z0-9_-]+):\s*(.*)$/);
      if (!matchKey || matchKey[1] !== key) {
        nextLines.push(current);
        continue;
      }

      replaced = true;
      nextLines.push(nextLine);
      const isBlockScalar = /^[>|]/.test(matchKey[2].trim());
      if (isBlockScalar || key === 'description') {
        while (i + 1 < lines.length && (/^\s+/.test(lines[i + 1]) || lines[i + 1].trim() === '')) {
          i += 1;
        }
      }
    }
    if (!replaced) nextLines.push(nextLine);
    lines = nextLines;
  }
  const block = lines.join('\n');
  return `---\n${block.trimEnd()}\n---\n${clean.slice(match[0].length).replace(/^\r?\n/, '')}`;
}

function titleFromText(text, fallback) {
  return parseFrontmatter(text).frontmatter.title || fallback;
}

function categoryFromText(text) {
  return parseFrontmatter(text).frontmatter.category || 'Software';
}

function topicSlug(value) {
  return String(value || 'software')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '') || 'software';
}

function opportunityBlock(site, opportunity, text) {
  const query = sanitizeText(opportunity.query, 'this search query');
  const title = sanitizeText(titleFromText(text, opportunity.page), 'this guide');
  const category = sanitizeText(categoryFromText(text), 'Software');
  const categorySlug = topicSlug(category);
  const actionLabel =
    {
      rewrite_title_meta: 'comparison and pricing angle behind that query',
      expand_striking_distance: 'shortlisting questions behind that near-page-one query',
      add_depth_and_internal_links: 'deeper evaluation path behind that query',
      reinforce_winner: 'next-step decision behind that winning query',
    }[opportunity.action] || 'search intent behind that query';

  return `

{/* ${MARKER}:${safeHash(`${site.siteUrl}:${opportunity.page}:${query}`)} */}

## Search Intent Update

Readers finding this page through **${query}** are usually not looking for a generic definition. They are trying to decide whether ${title} belongs in the current stack, whether the category is worth comparing now, and what evidence would make the decision safer.

### What To Check First

Start with the workflow owner and the measurable outcome. If the tool changes a customer-facing promise, a revenue workflow, a production workflow, or a compliance-sensitive process, the shortlist needs review controls and reporting before a pilot starts. If it only supports internal research, a lighter experiment is enough.

### How To Use This Page

This page should answer the ${actionLabel} intent before sending the reader deeper into the site. Compare the category fit, check the implementation risk, then use the [${category} topic hub](/blog/topics/${categorySlug}) to move to adjacent guides without losing the original decision context.

### FAQ

#### Is ${query} a buying-intent query?

It should be treated as a buying or implementation-intent query when the reader is comparing options, looking for workflow examples, or trying to justify a tool decision. In that case, the next useful step is a focused shortlist, not a broad market overview.

#### What should the team do after reading?

Pick one workflow, one owner, one success metric, and one rollback condition. If a product cannot improve that narrow workflow within a short pilot, keep the research but avoid adding another tool to the operating stack.

<InlineCTA variant="calculator" toolName="${category.replace(/"/g, '&quot;')} stack" categorySlug="${categorySlug}" />
`;
}

function applyContentUpdates(gsc, args) {
  const changedFiles = [];
  const siteResults = [];

  for (const siteReport of gsc.sites.filter((site) => CORE_SITES.includes(site.site))) {
    const site = SITES[siteReport.site];
    const status = gitStatus(site.localDir);
    const siteResult = {
      site: siteReport.site,
      skipped: false,
      reason: '',
      changed: 0,
      files: [],
    };

    if (!status.ok || status.dirty) {
      siteResult.skipped = true;
      siteResult.reason = status.ok ? 'dirty_worktree' : 'git_status_failed';
      siteResults.push(siteResult);
      continue;
    }

    const uniqueByFile = new Map();
    for (const opportunity of siteReport.opportunities) {
      if (!opportunity.localFile) continue;
      if (!uniqueByFile.has(opportunity.localFile)) uniqueByFile.set(opportunity.localFile, opportunity);
    }

    for (const opportunity of Array.from(uniqueByFile.values()).slice(0, args.maxApplyPerSite)) {
      const file = path.join(ROOT, opportunity.localFile);
      if (!fs.existsSync(file)) continue;
      const before = fs.readFileSync(file, 'utf8');
      const marker = `${MARKER}:${safeHash(`${site.siteUrl}:${opportunity.page}:${opportunity.query}`)}`;
      if (before.includes(marker)) continue;
      const description = `${sanitizeText(opportunity.query)} decision guide for ${site.name}: compare fit, risks, implementation notes, and next actions.`;
      const withFrontmatter = updateFrontmatter(before, {
        description: description.slice(0, 155),
        updatedDate: kstDateOffset(0),
      });
      const next = `${withFrontmatter.trimEnd()}${opportunityBlock(site, opportunity, withFrontmatter)}\n`;
      fs.writeFileSync(file, next, 'utf8');
      siteResult.changed += 1;
      siteResult.files.push(opportunity.localFile);
      changedFiles.push(opportunity.localFile);
    }

    siteResults.push(siteResult);
  }

  return {
    enabled: args.applyContent,
    changedFileCount: changedFiles.length,
    changedFiles,
    sites: siteResults,
  };
}

function walkFiles(dir, predicate, limit = 3000) {
  const results = [];
  const stack = [dir];
  while (stack.length && results.length < limit) {
    const current = stack.pop();
    if (!current || !fs.existsSync(current)) continue;
    for (const entry of fs.readdirSync(current, { withFileTypes: true })) {
      const full = path.join(current, entry.name);
      if (entry.isDirectory()) {
        if (!['node_modules', '.next', '.git', 'dist', 'out'].includes(entry.name)) stack.push(full);
      } else if (predicate(full)) {
        results.push(full);
      }
    }
  }
  return results;
}

function auditPosthog(siteIds) {
  const sites = [];
  for (const siteId of siteIds.filter((site) => CORE_SITES.includes(site))) {
    const site = SITES[siteId];
    const files = walkFiles(path.join(site.localDir, 'src'), (file) => /\.(ts|tsx|js|jsx)$/.test(file), 1500);
    const combined = files.map((file) => fs.readFileSync(file, 'utf8')).join('\n');
    const hasProvider = /PostHogProvider|posthog\.init|posthog-js/.test(combined);
    const required = Object.fromEntries(REQUIRED_POSTHOG_EVENTS.map((event) => [event, combined.includes(event)]));
    const recommended = Object.fromEntries(RECOMMENDED_POSTHOG_EVENTS.map((event) => [event, combined.includes(event)]));
    const requiredMissing = Object.entries(required).filter(([, ok]) => !ok).map(([event]) => event);
    const recommendedMissing = Object.entries(recommended).filter(([, ok]) => !ok).map(([event]) => event);
    sites.push({
      site: siteId,
      hasProvider,
      required,
      recommended,
      requiredMissing,
      recommendedMissing,
      status: hasProvider && requiredMissing.length === 0 ? 'green' : 'red',
    });
  }

  return {
    requiredEvents: REQUIRED_POSTHOG_EVENTS,
    recommendedEvents: RECOMMENDED_POSTHOG_EVENTS,
    passed: sites.every((site) => site.status === 'green'),
    sites,
  };
}

function localLatestPost(site) {
  const dirs = [
    path.join(site.localDir || '', 'content', 'blog'),
    path.join(site.localDir || '', 'src', 'content', 'blog'),
  ];
  const blogDir = dirs.find((dir) => fs.existsSync(dir));
  if (!blogDir) return null;
  const posts = fs.readdirSync(blogDir)
    .filter((name) => name.endsWith('.mdx'))
    .map((name) => {
      const file = path.join(blogDir, name);
      const text = fs.readFileSync(file, 'utf8');
      const { frontmatter } = parseFrontmatter(text);
      return {
        slug: name.replace(/\.mdx$/, ''),
        title: frontmatter.title || name.replace(/\.mdx$/, ''),
        date: String(frontmatter.date || '').slice(0, 10),
      };
    })
    .filter((post) => /^\d{4}-\d{2}-\d{2}$/.test(post.date))
    .sort((a, b) => b.date.localeCompare(a.date));
  return posts[0] || null;
}

function daysSince(dateText) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(dateText || '')) return null;
  const today = new Date(`${kstDateOffset(0)}T00:00:00+09:00`);
  const date = new Date(`${dateText}T00:00:00+09:00`);
  return Math.floor((today.getTime() - date.getTime()) / 86400000);
}

function hasNpmScript(site, scriptName) {
  const packageFile = path.join(site.localDir || '', 'package.json');
  if (!fs.existsSync(packageFile)) return false;
  try {
    const json = JSON.parse(fs.readFileSync(packageFile, 'utf8'));
    return Boolean(json.scripts?.[scriptName]);
  } catch {
    return false;
  }
}

async function auditPipeline(siteIds, gsc, args) {
  const sites = [];
  for (const siteId of siteIds.filter((site) => CORE_SITES.includes(site))) {
    const site = SITES[siteId];
    const latest = localLatestPost(site);
    const staleDays = latest ? daysSince(latest.date) : null;
    const [blog, detail, sitemap, robots, cron] = await Promise.all([
      fetchText(`${site.domain}/blog`),
      latest ? fetchText(`${site.domain}/blog/${latest.slug}`) : Promise.resolve({ ok: false, status: 0, text: '' }),
      fetchText(`${site.domain}/sitemap.xml`),
      fetchText(`${site.domain}/robots.txt`),
      fetchText(`${site.domain}/api/hive-mind/orchestrate`),
    ]);
    const gscSite = gsc.sites.find((entry) => entry.site === siteId);
    const issues = [];
    if (!latest) issues.push('no_local_latest_post');
    if (staleDays === null || staleDays > args.maxStaleDays) issues.push('latest_post_stale');
    if (!blog.ok || !blog.text.includes(latest?.slug || '__missing__')) issues.push('live_blog_missing_latest');
    if (!detail.ok || !detail.text.includes(latest?.title || '__missing__')) issues.push('live_detail_missing_latest');
    if (!sitemap.ok || !sitemap.text.includes(`/blog/${latest?.slug || '__missing__'}`)) issues.push('sitemap_missing_latest');
    if (!robots.ok || !/sitemap:/i.test(robots.text)) issues.push('robots_missing_sitemap');
    if (!hasNpmScript(site, 'indexnow:submit')) issues.push('indexnow_submit_script_missing');
    if (![401, 403, 405].includes(cron.status)) issues.push('cron_route_unprotected_or_unexpected');
    if (!gscSite?.propertyListed || !gscSite?.sitemapKnown) issues.push('gsc_property_or_sitemap_not_ready');

    sites.push({
      site: siteId,
      latest,
      staleDays,
      live: {
        blog: { status: blog.status, ok: blog.ok && blog.text.includes(latest?.slug || '__missing__') },
        detail: { status: detail.status, ok: detail.ok && detail.text.includes(latest?.title || '__missing__') },
        sitemap: { status: sitemap.status, ok: sitemap.ok && sitemap.text.includes(`/blog/${latest?.slug || '__missing__'}`) },
        robots: { status: robots.status, ok: robots.ok && /sitemap:/i.test(robots.text) },
        cron: { status: cron.status, protected: [401, 403, 405].includes(cron.status) },
      },
      indexnowSubmitScript: hasNpmScript(site, 'indexnow:submit'),
      gscReady: Boolean(gscSite?.propertyListed && gscSite?.sitemapKnown),
      status: issues.length ? 'red' : 'green',
      issues,
    });
  }

  return {
    maxStaleDays: args.maxStaleDays,
    passed: sites.every((site) => site.status === 'green'),
    sites,
  };
}

function markdown(report) {
  const lines = [
    '# SBU Search Growth Flywheel',
    '',
    `- generatedAt: ${report.generatedAt}`,
    `- passed: ${report.passed}`,
    `- gscRange: ${report.gsc.startDate}..${report.gsc.endDate}`,
    `- gscCredentialSource: ${report.gsc.credential?.source || 'unknown'}`,
    `- gscPropertiesListed: ${report.gsc.propertyListedOk}/${report.gsc.sites.length}`,
    `- gscSitemapsKnown: ${report.gsc.sitemapKnownOk}/${report.gsc.sites.length}`,
    `- gscOpportunities: ${report.gsc.opportunityCount}`,
    `- contentApplyEnabled: ${report.contentApply.enabled}`,
    `- contentChangedFiles: ${report.contentApply.changedFileCount}`,
    '',
    '## GSC Sites',
    '',
    '| Site | Owner | Sitemap | Rows | Opportunities | No Data Yet |',
    '|---|---:|---:|---:|---:|---:|',
  ];

  for (const site of report.gsc.sites) {
    lines.push(
      `| ${site.site} | ${site.permission || 'none'} | ${site.sitemapKnown} | ${site.searchAnalytics.rowCount} | ${site.opportunities.length} | ${site.searchAnalytics.noDataYet} |`,
    );
  }

  if (report.gsc.credentialAttempts?.length) {
    lines.push('', '## GSC Credential Attempts', '', '| Source | Stage | Status | OK | Site Count |', '|---|---:|---:|---:|---:|');
    for (const attempt of report.gsc.credentialAttempts) {
      lines.push(
        `| ${attempt.source} | ${attempt.stage} | ${attempt.status || '-'} | ${attempt.ok} | ${attempt.siteCount || 0} |`,
      );
    }
  }

  lines.push('', '## Pipeline Gate', '', '| Site | Status | Latest | Live Blog | Detail | Sitemap | Cron | Issues |', '|---|---:|---|---:|---:|---:|---:|---|');
  for (const site of report.pipeline.sites) {
    lines.push(
      `| ${site.site} | ${site.status} | ${site.latest?.slug || 'missing'} | ${site.live.blog.ok} | ${site.live.detail.ok} | ${site.live.sitemap.ok} | ${site.live.cron.protected} | ${site.issues.join(', ')} |`,
    );
  }

  lines.push('', '## PostHog Taxonomy', '', '| Site | Status | Missing Required | Missing Recommended |', '|---|---:|---|---|');
  for (const site of report.posthogTaxonomy.sites) {
    lines.push(
      `| ${site.site} | ${site.status} | ${site.requiredMissing.join(', ') || '-'} | ${site.recommendedMissing.join(', ') || '-'} |`,
    );
  }

  if (report.contentApply.changedFiles.length) {
    lines.push('', '## Changed Files', '');
    for (const file of report.contentApply.changedFiles) lines.push(`- ${file}`);
  }

  return `${lines.join('\n')}\n`;
}

function writeReport(report) {
  fs.mkdirSync(OUT_DIR, { recursive: true });
  const stamp = report.generatedAt.replace(/[:+]/g, '-');
  const json = `${JSON.stringify(report, null, 2)}\n`;
  const md = markdown(report);
  fs.writeFileSync(path.join(OUT_DIR, `search-growth-flywheel-${stamp}.json`), json, 'utf8');
  fs.writeFileSync(path.join(OUT_DIR, `search-growth-flywheel-${stamp}.md`), md, 'utf8');
  fs.writeFileSync(path.join(OUT_DIR, 'search-growth-flywheel-latest.json'), json, 'utf8');
  fs.writeFileSync(path.join(OUT_DIR, 'search-growth-flywheel-latest.md'), md, 'utf8');
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const siteIds = args.sites.split(',').map((site) => site.trim()).filter(Boolean);
  const unknown = siteIds.filter((site) => !SITES[site]);
  if (unknown.length) throw new Error(`Unknown sites: ${unknown.join(', ')}`);

  const tokenResult = await getSearchConsoleToken(['https://www.googleapis.com/auth/webmasters']);
  if (!tokenResult.ok) {
    const attemptSummary = (tokenResult.attempts || [])
      .map((attempt) => `${attempt.source}:${attempt.stage}:${attempt.status || attempt.error || 'failed'}`)
      .join(', ');
    throw new Error(`Search Console credential unavailable: ${tokenResult.error}${attemptSummary ? ` (${attemptSummary})` : ''}`);
  }

  const gsc = await collectGsc(
    tokenResult.token,
    siteIds,
    args,
    tokenResult.listResponse,
    tokenResult.credential,
    tokenResult.attempts,
  );
  const contentApply = args.applyContent ? applyContentUpdates(gsc, args) : {
    enabled: false,
    changedFileCount: 0,
    changedFiles: [],
    sites: [],
  };
  const posthogTaxonomy = auditPosthog(siteIds);
  const pipeline = await auditPipeline(siteIds, gsc, args);

  const report = {
    generatedAt: nowKst(),
    args: {
      sites: siteIds,
      days: args.days,
      minImpressions: args.minImpressions,
      rowLimit: args.rowLimit,
      applyContent: args.applyContent,
      maxApplyPerSite: args.maxApplyPerSite,
      maxStaleDays: args.maxStaleDays,
    },
    gsc,
    contentApply,
    posthogTaxonomy,
    pipeline,
    passed:
      gsc.propertyListedOk === gsc.sites.length &&
      gsc.sitemapKnownOk === gsc.sites.length &&
      posthogTaxonomy.passed &&
      pipeline.passed,
  };

  writeReport(report);
  if (args.json) console.log(JSON.stringify(report, null, 2));
  else console.log(markdown(report));
  if (!report.passed) process.exit(1);
}

main().catch((error) => {
  console.error(error?.message || error);
  process.exit(1);
});
