/**
 * GA4 all-site report with shared-property host filtering.
 * Usage: node scripts/ga4-all-report.mjs
 */
import { createSign } from 'crypto';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const ROOT = resolve(import.meta.dirname, '..');
const ENV_PATH = resolve(ROOT, '.env');

function readEnvFile(filePath) {
  const env = {};
  const raw = readFileSync(filePath, 'utf-8');
  for (const line of raw.split(/\r?\n/)) {
    if (!line || line.trim().startsWith('#')) continue;
    const idx = line.indexOf('=');
    if (idx < 0) continue;
    const key = line.slice(0, idx).trim();
    let value = line.slice(idx + 1).trim();
    value = value.replace(/^"(.*)"$/, '$1');
    env[key] = value;
  }
  return env;
}

const env = readEnvFile(ENV_PATH);
const saPath = env.GA4_SERVICE_ACCOUNT_PATH;
if (!saPath) {
  throw new Error('GA4_SERVICE_ACCOUNT_PATH is missing in .env');
}

const credentials = JSON.parse(readFileSync(saPath, 'utf-8'));

const SITES = [
  { name: 'NeoGenesis', propertyId: '526345390', host: 'neogenesis.app' },
  { name: 'ToolPick', propertyId: '524659689' },
  { name: 'UR WRONG', propertyId: '524964770' },
  { name: 'K-OTT', propertyId: '525765817' },
  { name: 'HeoYesol Portfolio', propertyId: '524705454' },
  { name: 'AIForge', propertyId: '526345390', host: 'aiforge.neogenesis.app' },
  { name: 'CraftDesk', propertyId: '526345390', host: 'craftdesk.neogenesis.app' },
  { name: 'DeployStack', propertyId: '526345390', host: 'deploystack.neogenesis.app' },
  { name: 'FinStack', propertyId: '526345390', host: 'finstack.neogenesis.app' },
  { name: 'SellKit', propertyId: '526345390', host: 'sellkit.neogenesis.app' },
  { name: 'ReviewLab', propertyId: '526345390', host: 'review.neogenesis.app' },
  { name: 'EthicaAI', propertyId: '526345390', host: 'ethica.neogenesis.app' },
  { name: 'WhyLab', propertyId: '526345390', host: 'whylab.neogenesis.app' },
];

async function getAccessToken() {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: 'RS256', typ: 'JWT' };
  const payload = {
    iss: credentials.client_email,
    scope: 'https://www.googleapis.com/auth/analytics.readonly',
    aud: 'https://oauth2.googleapis.com/token',
    iat: now,
    exp: now + 3600,
  };
  const h = Buffer.from(JSON.stringify(header)).toString('base64url');
  const p = Buffer.from(JSON.stringify(payload)).toString('base64url');
  const sign = createSign('RSA-SHA256');
  sign.update(`${h}.${p}`);
  const sig = sign.sign(credentials.private_key, 'base64url');
  const jwt = `${h}.${p}.${sig}`;

  const res = await fetch('https://oauth2.googleapis.com/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer&assertion=${jwt}`,
  });
  if (!res.ok) throw new Error(await res.text());
  return (await res.json()).access_token;
}

async function queryGA4(token, site, startDate, endDate) {
  const body = {
    dateRanges: [{ startDate, endDate }],
    metrics: [
      { name: 'sessions' },
      { name: 'screenPageViews' },
      { name: 'activeUsers' },
      { name: 'newUsers' },
      { name: 'bounceRate' },
      { name: 'averageSessionDuration' },
    ],
  };
  if (site.host) {
    body.dimensionFilter = {
      filter: {
        fieldName: 'hostName',
        stringFilter: { matchType: 'EXACT', value: site.host },
      },
    };
  }

  const res = await fetch(
    `https://analyticsdata.googleapis.com/v1beta/properties/${site.propertyId}:runReport`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }
  );
  if (!res.ok) {
    throw new Error(await res.text());
  }
  const data = await res.json();
  const row = data.rows?.[0]?.metricValues;
  if (!row) return null;
  return {
    sessions: Number.parseInt(row[0].value, 10) || 0,
    pageViews: Number.parseInt(row[1].value, 10) || 0,
    activeUsers: Number.parseInt(row[2].value, 10) || 0,
    newUsers: Number.parseInt(row[3].value, 10) || 0,
    bounceRate: `${(Number.parseFloat(row[4].value) * 100).toFixed(1)}%`,
    avgDuration: `${Math.round(Number.parseFloat(row[5].value))}s`,
  };
}

async function queryTrend(token, site) {
  const body = {
    dateRanges: [{ startDate: '7daysAgo', endDate: 'today' }],
    metrics: [{ name: 'sessions' }],
    dimensions: [{ name: 'date' }],
    orderBys: [{ dimension: { dimensionName: 'date' } }],
  };
  if (site.host) {
    body.dimensionFilter = {
      filter: {
        fieldName: 'hostName',
        stringFilter: { matchType: 'EXACT', value: site.host },
      },
    };
  }

  const res = await fetch(
    `https://analyticsdata.googleapis.com/v1beta/properties/${site.propertyId}:runReport`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }
  );
  if (!res.ok) return [];
  const data = await res.json();
  return (data.rows || []).map((row) => ({
    date: row.dimensionValues[0].value,
    sessions: Number.parseInt(row.metricValues[0].value, 10) || 0,
  }));
}

async function main() {
  console.log('GA4 token request...');
  const token = await getAccessToken();
  console.log('Token OK');
  console.log('NOTE: NeoGenesis subdomains use the shared property 526345390 with hostName filters.\n');

  const periods = [
    { label: 'Today', start: 'today', end: 'today' },
    { label: 'Last 7d', start: '7daysAgo', end: 'today' },
    { label: 'Last 30d', start: '30daysAgo', end: 'today' },
    { label: 'Last 90d', start: '90daysAgo', end: 'today' },
  ];

  const results = [];
  for (const site of SITES) {
    process.stdout.write(`Querying ${site.name.padEnd(18)} `);
    const data = {};
    for (const period of periods) {
      try {
        data[period.label] = await queryGA4(token, site, period.start, period.end);
      } catch {
        data[period.label] = null;
      }
    }
    let trend = [];
    try {
      trend = await queryTrend(token, site);
    } catch {}
    results.push({ ...site, data, trend });
    console.log('OK');
  }

  console.log(`\n${'='.repeat(90)}`);
  console.log(`NEO-GENESIS GA4 Traffic Report (${new Date().toLocaleDateString('ko-KR')})`);
  console.log('='.repeat(90));
  console.log('\n[Last 30d Summary]\n');
  console.log('Site               | Sessions | PageViews | ActiveUsers | NewUsers | Bounce | AvgDuration');
  console.log('-'.repeat(90));

  let totalSessions = 0;
  let totalPV = 0;
  let totalUsers = 0;
  let totalNew = 0;

  for (const result of results) {
    const d = result.data['Last 30d'];
    if (!d) {
      console.log(`${result.name.padEnd(18)} | NO DATA`);
      continue;
    }
    totalSessions += d.sessions;
    totalPV += d.pageViews;
    totalUsers += d.activeUsers;
    totalNew += d.newUsers;
    console.log(
      `${result.name.padEnd(18)} | ${String(d.sessions).padStart(8)} | ${String(d.pageViews).padStart(9)} | ` +
      `${String(d.activeUsers).padStart(11)} | ${String(d.newUsers).padStart(8)} | ${d.bounceRate.padStart(6)} | ${d.avgDuration}`
    );
  }

  console.log('-'.repeat(90));
  console.log(
    `${'TOTAL'.padEnd(18)} | ${String(totalSessions).padStart(8)} | ${String(totalPV).padStart(9)} | ` +
    `${String(totalUsers).padStart(11)} | ${String(totalNew).padStart(8)}`
  );
}

main().catch((error) => {
  console.error('ERROR:', error.message);
  process.exit(1);
});
