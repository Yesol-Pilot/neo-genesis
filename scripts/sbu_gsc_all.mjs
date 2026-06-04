#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT_DIR = path.join(ROOT, 'data', 'sbu-growth');
const TOKEN_URL = 'https://oauth2.googleapis.com/token';
const WEBMASTERS_SCOPE = 'https://www.googleapis.com/auth/webmasters';
const DEFAULT_SITE_IDS = [
  'toolpick',
  'aiforge',
  'craftdesk',
  'deploystack',
  'finstack',
  'sellkit',
  'reviewlab',
  'ur-wrong',
  'kott',
  'whylab',
  'ethicaai',
  'neogenesis',
  'heoyesol',
];
const DEFAULT_SITES = DEFAULT_SITE_IDS.join(',');

const SITES = {
  toolpick: {
    name: 'ToolPick',
    property: 'sc-domain:toolpick.dev',
    domain: 'https://www.toolpick.dev',
    host: 'toolpick.dev',
    sitemap: 'https://www.toolpick.dev/sitemap.xml',
  },
  aiforge: {
    name: 'AIForge',
    property: 'https://aiforge.neogenesis.app/',
    domain: 'https://aiforge.neogenesis.app',
    host: 'aiforge.neogenesis.app',
    sitemap: 'https://aiforge.neogenesis.app/sitemap.xml',
  },
  craftdesk: {
    name: 'CraftDesk',
    property: 'https://craftdesk.neogenesis.app/',
    domain: 'https://craftdesk.neogenesis.app',
    host: 'craftdesk.neogenesis.app',
    sitemap: 'https://craftdesk.neogenesis.app/sitemap.xml',
  },
  deploystack: {
    name: 'DeployStack',
    property: 'https://deploystack.neogenesis.app/',
    domain: 'https://deploystack.neogenesis.app',
    host: 'deploystack.neogenesis.app',
    sitemap: 'https://deploystack.neogenesis.app/sitemap.xml',
  },
  finstack: {
    name: 'FinStack',
    property: 'https://finstack.neogenesis.app/',
    domain: 'https://finstack.neogenesis.app',
    host: 'finstack.neogenesis.app',
    sitemap: 'https://finstack.neogenesis.app/sitemap.xml',
  },
  sellkit: {
    name: 'SellKit',
    property: 'https://sellkit.neogenesis.app/',
    domain: 'https://sellkit.neogenesis.app',
    host: 'sellkit.neogenesis.app',
    sitemap: 'https://sellkit.neogenesis.app/sitemap.xml',
  },
  reviewlab: {
    name: 'ReviewLab',
    property: 'https://review.neogenesis.app/',
    domain: 'https://review.neogenesis.app',
    host: 'review.neogenesis.app',
    sitemap: 'https://review.neogenesis.app/sitemap.xml',
  },
  'ur-wrong': {
    name: 'UR WRONG',
    property: 'https://ur-wrong.com/',
    domain: 'https://ur-wrong.com',
    host: 'ur-wrong.com',
    sitemap: 'https://ur-wrong.com/sitemap.xml',
  },
  kott: {
    name: 'K-OTT',
    property: 'https://kott.kr/',
    domain: 'https://kott.kr',
    host: 'kott.kr',
    sitemap: 'https://kott.kr/sitemap.xml',
  },
  whylab: {
    name: 'WhyLab',
    property: 'https://whylab.neogenesis.app/',
    domain: 'https://whylab.neogenesis.app',
    host: 'whylab.neogenesis.app',
    sitemap: 'https://whylab.neogenesis.app/sitemap.xml',
  },
  ethicaai: {
    name: 'EthicaAI',
    property: 'https://ethica.neogenesis.app/',
    domain: 'https://ethica.neogenesis.app',
    host: 'ethica.neogenesis.app',
    sitemap: 'https://ethica.neogenesis.app/sitemap.xml',
  },
  neogenesis: {
    name: 'NeoGenesis',
    property: 'https://neogenesis.app/',
    domain: 'https://neogenesis.app',
    host: 'neogenesis.app',
    sitemap: 'https://neogenesis.app/sitemap.xml',
  },
  heoyesol: {
    name: 'HeoYesol Portfolio',
    property: 'sc-domain:heoyesol.kr',
    domain: 'https://heoyesol.kr',
    host: 'heoyesol.kr',
    sitemap: 'https://heoyesol.kr/sitemap.xml',
  },
};

function parseArgs(argv) {
  const args = {
    sites: DEFAULT_SITES,
    days: 28,
    rowLimit: 2500,
    submitSitemaps: false,
    fetch: false,
    minImpressions: 1,
    writeDefaultLatest: false,
  };

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--sites') args.sites = argv[++i] || args.sites;
    else if (arg === '--days') args.days = Number(argv[++i] || args.days);
    else if (arg === '--row-limit') args.rowLimit = Number(argv[++i] || args.rowLimit);
    else if (arg === '--min-impressions') args.minImpressions = Number(argv[++i] || args.minImpressions);
    else if (arg === '--submit-sitemaps') args.submitSitemaps = true;
    else if (arg === '--fetch') args.fetch = true;
    else if (arg === '--write-default-latest') args.writeDefaultLatest = true;
    else if (arg === '--all') {
      args.submitSitemaps = true;
      args.fetch = true;
    }
  }

  return args;
}

function sameSiteSet(left, right) {
  if (left.length !== right.length) return false;
  const rightSet = new Set(right);
  return left.every((siteId) => rightSet.has(siteId));
}

function safeScopeSlug(siteIds) {
  if (siteIds.length <= 3) return siteIds.join('-').replace(/[^a-z0-9-]/gi, '-').toLowerCase();
  return crypto.createHash('sha1').update(siteIds.join(',')).digest('hex').slice(0, 12);
}

function outputScopeForSites(siteIds, args) {
  const isDefaultAll = sameSiteSet(siteIds, DEFAULT_SITE_IDS);
  const label = isDefaultAll ? 'all-sbu' : `scope-${safeScopeSlug(siteIds)}`;
  return {
    label,
    siteIds,
    isDefaultAll,
    filePrefix: isDefaultAll ? 'gsc-all-sbu' : `gsc-sbu-${label}`,
    writesDefaultLatest: isDefaultAll || args.writeDefaultLatest,
  };
}

function loadEnvFiles() {
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
      if (key && value && !process.env[key]) process.env[key] = value;
    }
  }
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

function dateOffset(days) {
  const now = new Date();
  const kst = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  kst.setDate(kst.getDate() + days);
  return [
    kst.getFullYear(),
    String(kst.getMonth() + 1).padStart(2, '0'),
    String(kst.getDate()).padStart(2, '0'),
  ].join('-');
}

function dateRange(days) {
  const endDate = dateOffset(-2);
  const start = new Date(`${endDate}T00:00:00+09:00`);
  start.setDate(start.getDate() - Math.max(1, days) + 1);
  return { startDate: start.toISOString().slice(0, 10), endDate };
}

function readJson(filePath) {
  if (!filePath || !fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function normalizeOAuthClient(rawClient) {
  const client = rawClient?.installed || rawClient?.web || rawClient;
  if (!client?.client_id || !client?.client_secret) return null;
  return client;
}

function base64url(input) {
  return Buffer.from(input)
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '');
}

async function tokenFromServiceAccount(scope) {
  const raw = process.env.GOOGLE_SERVICE_ACCOUNT_JSON
    ? JSON.parse(process.env.GOOGLE_SERVICE_ACCOUNT_JSON)
    : readJson(process.env.GOOGLE_APPLICATION_CREDENTIALS);
  if (!raw?.client_email || !raw?.private_key) return null;

  const now = Math.floor(Date.now() / 1000);
  const unsigned = `${base64url(JSON.stringify({ alg: 'RS256', typ: 'JWT' }))}.${base64url(
    JSON.stringify({
      iss: raw.client_email,
      scope,
      aud: raw.token_uri || TOKEN_URL,
      iat: now,
      exp: now + 3600,
    }),
  )}`;
  const signer = crypto.createSign('RSA-SHA256');
  signer.update(unsigned);
  signer.end();
  const assertion = `${unsigned}.${signer.sign(raw.private_key, 'base64url')}`;
  const response = await fetch(raw.token_uri || TOKEN_URL, {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
      assertion,
    }),
  });
  const json = await response.json();
  if (!response.ok) throw new Error(`service_account_token_failed_${response.status}`);
  return { token: json.access_token, source: 'service_account' };
}

async function tokenFromRefreshToken() {
  if (!process.env.GOOGLE_SEARCH_CONSOLE_REFRESH_TOKEN) return null;
  const client = normalizeOAuthClient(readJson(process.env.GOOGLE_OAUTH_CLIENT_SECRET_FILE)) || {
    client_id: process.env.GOOGLE_OAUTH_CLIENT_ID,
    client_secret: process.env.GOOGLE_OAUTH_CLIENT_SECRET,
  };
  if (!client?.client_id || !client?.client_secret) throw new Error('missing_google_oauth_client');

  const response = await fetch(TOKEN_URL, {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      client_id: client.client_id,
      client_secret: client.client_secret,
      refresh_token: process.env.GOOGLE_SEARCH_CONSOLE_REFRESH_TOKEN,
      grant_type: 'refresh_token',
    }),
  });
  const json = await response.json();
  if (!response.ok) throw new Error(`refresh_token_failed_${response.status}_${json.error || 'unknown'}`);
  return { token: json.access_token, source: 'refresh_token' };
}

async function resolveToken() {
  if (process.env.GOOGLE_SEARCH_CONSOLE_ACCESS_TOKEN) {
    return { token: process.env.GOOGLE_SEARCH_CONSOLE_ACCESS_TOKEN, source: 'access_token' };
  }

  try {
    const refreshToken = await tokenFromRefreshToken();
    if (refreshToken) return refreshToken;
  } catch (error) {
    console.warn(`[gsc] refresh token unavailable, trying service account fallback: ${error.message}`);
  }

  return tokenFromServiceAccount(WEBMASTERS_SCOPE);
}

async function fetchText(url) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(url, {
      signal: controller.signal,
      redirect: 'follow',
      headers: { 'user-agent': 'neo-sbu-gsc-all/1.0' },
    });
    return { ok: response.ok, status: response.status, text: await response.text(), finalUrl: response.url };
  } catch (error) {
    return { ok: false, status: 0, text: '', error: String(error?.message || error) };
  } finally {
    clearTimeout(timeout);
  }
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      'user-agent': 'neo-sbu-gsc-all/1.0',
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  let json = null;
  try {
    json = text ? JSON.parse(text) : null;
  } catch {}
  return { ok: response.ok, status: response.status, json, text: text.slice(0, 800) };
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function summarizeRows(rows, minImpressions) {
  const byPage = new Map();
  for (const row of rows) {
    const [query, page] = row.keys || ['', ''];
    const impressions = Number(row.impressions || 0);
    if (impressions < minImpressions) continue;
    const clicks = Number(row.clicks || 0);
    const ctr = Number(row.ctr || 0);
    const position = Number(row.position || 0);
    const score = Number((impressions * Math.max(0.01, 0.08 - ctr) * (position ? 1 / Math.sqrt(position) : 0.2)).toFixed(4));
    const item = byPage.get(page) || {
      page,
      clicks: 0,
      impressions: 0,
      weightedPosition: 0,
      queries: [],
      score: 0,
    };
    item.clicks += clicks;
    item.impressions += impressions;
    item.weightedPosition += position * impressions;
    item.score += score;
    item.queries.push({ query, clicks, impressions, ctr, position, score });
    byPage.set(page, item);
  }

  return [...byPage.values()]
    .map((item) => ({
      ...item,
      averagePosition: item.impressions ? Number((item.weightedPosition / item.impressions).toFixed(2)) : 0,
      score: Number(item.score.toFixed(4)),
      queries: item.queries.sort((a, b) => b.score - a.score).slice(0, 5),
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 10);
}

function isScopeInsufficient(response) {
  return response?.status === 403
    && /ACCESS_TOKEN_SCOPE_INSUFFICIENT|insufficient authentication scopes|Insufficient Permission/i.test(response.text || '');
}

async function submitSitemap(encodedProperty, encodedSitemap, token) {
  return fetchJson(`https://www.googleapis.com/webmasters/v3/sites/${encodedProperty}/sitemaps/${encodedSitemap}`, {
    method: 'PUT',
    headers: { authorization: `Bearer ${token}`, 'content-type': 'application/json' },
  });
}

async function inspectSite(siteId, site, args, token, listedProperties, resolveSubmitFallbackToken) {
  const headers = { authorization: `Bearer ${token}`, 'content-type': 'application/json' };
  const liveSitemap = await fetchText(site.sitemap);
  const liveLocCount = (liveSitemap.text.match(/<loc>/g) || []).length;
  const encodedProperty = encodeURIComponent(site.property);
  const encodedSitemap = encodeURIComponent(site.sitemap);
  const gscSitemap = await fetchJson(`https://www.googleapis.com/webmasters/v3/sites/${encodedProperty}/sitemaps/${encodedSitemap}`, {
    headers,
  });
  await sleep(250);

  let sitemapSubmit = null;
  if (args.submitSitemaps) {
    sitemapSubmit = await submitSitemap(encodedProperty, encodedSitemap, token);
    if (isScopeInsufficient(sitemapSubmit) && resolveSubmitFallbackToken) {
      const fallback = await resolveSubmitFallbackToken();
      if (fallback?.token) {
        const retry = await submitSitemap(encodedProperty, encodedSitemap, fallback.token);
        retry.primaryStatus = sitemapSubmit.status;
        retry.primaryError = sitemapSubmit.text;
        retry.fallbackTokenSource = fallback.source;
        sitemapSubmit = retry;
      }
    }
    await sleep(350);
  }

  let searchAnalytics = null;
  let opportunities = [];
  if (args.fetch) {
    const { startDate, endDate } = dateRange(args.days);
    searchAnalytics = await fetchJson(`https://www.googleapis.com/webmasters/v3/sites/${encodedProperty}/searchAnalytics/query`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        startDate,
        endDate,
        dimensions: ['query', 'page'],
        rowLimit: args.rowLimit,
        dimensionFilterGroups: [
          {
            filters: [
              {
                dimension: 'page',
                operator: 'contains',
                expression: site.host,
              },
            ],
          },
        ],
      }),
    });
    opportunities = summarizeRows(searchAnalytics.json?.rows || [], args.minImpressions);
    await sleep(350);
  }

  return {
    id: siteId,
    name: site.name,
    property: site.property,
    domain: site.domain,
    sitemap: site.sitemap,
    propertyListed: listedProperties.has(site.property),
    permission: listedProperties.get(site.property) || null,
    liveSitemap: {
      ok: liveSitemap.ok,
      status: liveSitemap.status,
      locCount: liveLocCount,
      finalUrl: liveSitemap.finalUrl,
      error: liveSitemap.error || null,
    },
    gscSitemap: {
      ok: gscSitemap.ok,
      status: gscSitemap.status,
      known: gscSitemap.status === 200,
      error: gscSitemap.ok ? null : gscSitemap.text,
    },
    sitemapSubmit: sitemapSubmit
      ? {
          ok: sitemapSubmit.ok,
          status: sitemapSubmit.status,
          submitted: sitemapSubmit.status === 204,
          primaryStatus: sitemapSubmit.primaryStatus || null,
          fallbackTokenSource: sitemapSubmit.fallbackTokenSource || null,
          error: sitemapSubmit.ok ? null : sitemapSubmit.text,
        }
      : null,
    searchAnalytics: searchAnalytics
      ? {
          ok: searchAnalytics.ok,
          status: searchAnalytics.status,
          rows: searchAnalytics.json?.rows?.length || 0,
          error: searchAnalytics.ok ? null : searchAnalytics.text,
        }
      : null,
    opportunities,
  };
}

function renderMarkdown(report) {
  const lines = [
    '# SBU Search Console Automation',
    '',
    `Generated: ${report.generatedAt}`,
    `Token source: ${report.tokenSource}`,
    `Window: ${report.window.startDate} to ${report.window.endDate}`,
    `Scope: ${report.scope?.label || 'unknown'} (${(report.scope?.siteIds || []).join(', ')})`,
    `Writes default latest: ${Boolean(report.scope?.writesDefaultLatest)}`,
    '',
    '## Summary',
    '',
    `- Sites: ${report.summary.sites}`,
    `- Properties listed: ${report.summary.propertiesListed}/${report.summary.sites}`,
    `- Live sitemaps ok: ${report.summary.liveSitemapsOk}/${report.summary.sites}`,
    `- GSC sitemaps known: ${report.summary.gscSitemapsKnown}/${report.summary.sites}`,
    `- Sitemap submissions ok: ${report.summary.sitemapSubmissionsOk}/${report.summary.sitemapSubmissionsAttempted}`,
    `- Search Analytics fetch ok: ${report.summary.searchAnalyticsOk}/${report.summary.searchAnalyticsAttempted}`,
    `- Total rows: ${report.summary.totalRows}`,
    '',
    '## Sites',
    '',
    '| Site | Property | Listed | Permission | Live Sitemap | GSC Sitemap | Submit | Rows | Opportunities |',
    '|---|---|---:|---|---:|---:|---:|---:|---:|',
  ];

  for (const site of report.sites) {
    lines.push(
      `| ${site.name} | ${site.property} | ${site.propertyListed} | ${site.permission || 'none'} | ${site.liveSitemap.status}/${site.liveSitemap.locCount} | ${site.gscSitemap.status} | ${site.sitemapSubmit ? site.sitemapSubmit.status : 'skip'} | ${site.searchAnalytics ? site.searchAnalytics.rows : 'skip'} | ${site.opportunities.length} |`,
    );
  }

  lines.push('', '## Top Opportunities', '');
  for (const site of report.sites) {
    if (!site.opportunities.length) continue;
    lines.push(`### ${site.name}`, '');
    for (const opportunity of site.opportunities.slice(0, 5)) {
      const topQuery = opportunity.queries[0];
      lines.push(
        `- ${opportunity.page} | impressions ${opportunity.impressions}, clicks ${opportunity.clicks}, avg position ${opportunity.averagePosition}, top query "${topQuery?.query || ''}"`,
      );
    }
    lines.push('');
  }

  return `${lines.join('\n')}\n`;
}

async function main() {
  loadEnvFiles();
  const args = parseArgs(process.argv.slice(2));
  const siteIds = args.sites
    .split(',')
    .map((site) => site.trim())
    .filter(Boolean);
  const unknown = siteIds.filter((siteId) => !SITES[siteId]);
  if (unknown.length) throw new Error(`Unknown SBU site ids: ${unknown.join(', ')}`);
  const scope = outputScopeForSites(siteIds, args);

  const tokenResult = await resolveToken();
  if (!tokenResult?.token) throw new Error('missing_search_console_oauth_token');
  let submitFallbackTokenPromise = null;
  const resolveSubmitFallbackToken = async () => {
    if (tokenResult.source === 'service_account') return null;
    if (!submitFallbackTokenPromise) {
      submitFallbackTokenPromise = tokenFromServiceAccount(WEBMASTERS_SCOPE)
        .catch((error) => {
          console.warn(`[gsc] service account submit fallback unavailable: ${error.message}`);
          return null;
        });
    }
    return submitFallbackTokenPromise;
  };

  const headers = { authorization: `Bearer ${tokenResult.token}`, 'content-type': 'application/json' };
  const list = await fetchJson('https://www.googleapis.com/webmasters/v3/sites', { headers });
  if (!list.ok) throw new Error(`Search Console sites.list failed with ${list.status}`);
  const listedProperties = new Map((list.json?.siteEntry || []).map((entry) => [entry.siteUrl, entry.permissionLevel]));

  const sites = [];
  for (const siteId of siteIds) {
    sites.push(await inspectSite(siteId, SITES[siteId], args, tokenResult.token, listedProperties, resolveSubmitFallbackToken));
  }

  const attemptedSubmits = sites.filter((site) => site.sitemapSubmit).length;
  const attemptedSearch = sites.filter((site) => site.searchAnalytics).length;
  const { startDate, endDate } = dateRange(args.days);
  const report = {
    generatedAt: kstNow(),
    tokenSource: tokenResult.source,
    args,
    scope,
    window: { startDate, endDate },
    listedProperties: [...listedProperties.entries()].map(([siteUrl, permissionLevel]) => ({ siteUrl, permissionLevel })),
    summary: {
      sites: sites.length,
      propertiesListed: sites.filter((site) => site.propertyListed).length,
      liveSitemapsOk: sites.filter((site) => site.liveSitemap.ok).length,
      gscSitemapsKnown: sites.filter((site) => site.gscSitemap.known).length,
      sitemapSubmissionsAttempted: attemptedSubmits,
      sitemapSubmissionsOk: sites.filter((site) => site.sitemapSubmit?.submitted).length,
      searchAnalyticsAttempted: attemptedSearch,
      searchAnalyticsOk: sites.filter((site) => site.searchAnalytics?.ok).length,
      totalRows: sites.reduce((sum, site) => sum + (site.searchAnalytics?.rows || 0), 0),
    },
    sites,
  };
  const pass =
    report.summary.liveSitemapsOk === report.summary.sites &&
    (!args.fetch || report.summary.searchAnalyticsOk === report.summary.searchAnalyticsAttempted) &&
    (!args.submitSitemaps || report.summary.sitemapSubmissionsOk === report.summary.sitemapSubmissionsAttempted);

  fs.mkdirSync(OUT_DIR, { recursive: true });
  const stamp = report.generatedAt.replace(/[:+]/g, '-');
  const jsonOut = path.join(OUT_DIR, `${scope.filePrefix}-${stamp}.json`);
  const mdOut = path.join(OUT_DIR, `${scope.filePrefix}-${stamp}.md`);
  const latestJson = path.join(OUT_DIR, `${scope.filePrefix}-latest.json`);
  const latestMd = path.join(OUT_DIR, `${scope.filePrefix}-latest.md`);
  const defaultLatestJson = path.join(OUT_DIR, 'gsc-all-sbu-latest.json');
  const defaultLatestMd = path.join(OUT_DIR, 'gsc-all-sbu-latest.md');
  const markdown = renderMarkdown(report);

  for (const file of [jsonOut, latestJson]) fs.writeFileSync(file, JSON.stringify(report, null, 2));
  for (const file of [mdOut, latestMd]) fs.writeFileSync(file, markdown);
  if (scope.writesDefaultLatest) {
    if (latestJson !== defaultLatestJson) fs.writeFileSync(defaultLatestJson, JSON.stringify(report, null, 2));
    if (latestMd !== defaultLatestMd) fs.writeFileSync(defaultLatestMd, markdown);
  }

  console.log(JSON.stringify({
    pass,
    scope,
    latestJson,
    latestMd,
    defaultLatestJson: scope.writesDefaultLatest ? defaultLatestJson : null,
    defaultLatestMd: scope.writesDefaultLatest ? defaultLatestMd : null,
    summary: report.summary,
  }, null, 2));
  if (!pass) process.exitCode = 1;
}

main().catch((error) => {
  console.error(error.stack || error.message);
  process.exit(1);
});
