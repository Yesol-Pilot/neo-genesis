#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');
const OUT_DIR = path.join(ROOT, 'data', 'owner-analytics');
const GROWTH_DIR = path.join(ROOT, 'data', 'sbu-growth');
const SNAPSHOT_PATH = path.join(OUT_DIR, 'owner-traffic-latest.json');
const REGISTRY_PATH = path.join(OUT_DIR, 'site_registry.json');
const COVERAGE_PATH = path.join(OUT_DIR, 'source_coverage_matrix.json');
const ALLOWLIST_PATH = path.join(OUT_DIR, 'decision_event_allowlist.json');

const SNAPSHOT_VERSION = '2026-05-14.owner-traffic.v1';
const REGISTRY_VERSION = '2026-05-14.registry.v1';
const TIMEZONE = 'Asia/Seoul';
const KST_OFFSET_MS = 9 * 60 * 60 * 1000;
const DAY_MS = 24 * 60 * 60 * 1000;

const DECISION_EVENT_ALLOWLIST = {
  version: '2026-05-14.decision-events.v1',
  owner_goal: 'Count only events that can change an owner decision. Do not treat every non-pageview as a business action.',
  numerator_events: [
    'cta_click',
    'signup_intent',
    'pricing_view',
    'signup_click',
    'demo_request',
    'lead_submit',
    'subscribe_submit',
    'tool_submit',
    'search_submit',
    'filter_apply',
    'compare_select',
    'calculator_run',
    'download_click',
    'outbound_click',
    'outbound_official_click',
    'affiliate_click',
    'copy_link',
  ],
  denominator_event: '$pageview',
  excluded_events: [
    '$pageview',
    '$autocapture',
    '$pageleave',
    '$screen',
    '$web_vitals',
  ],
  dedupe_key: 'distinct_id + content_id + event + yyyy-mm-dd',
  session_rule: '30m inactivity window; do not assume identity merge unless PostHog provides it.',
  conversion_windows: {
    same_session: '30m',
    content_to_action: '7d',
  },
  internal_traffic_exclusions: [
    'localhost',
    '127.0.0.1',
    'preview deployments',
    'owner QA routes',
  ],
};

const REGISTRY = [
  {
    id: 'neogenesis',
    name: 'NeoGenesis',
    status: 'active_live',
    type: 'brand_hub',
    canonical_url: 'https://neogenesis.app',
    canonical_host: 'neogenesis.app',
    domain_aliases: ['neogenesis.app'],
    blog_url: 'https://neogenesis.app/blog',
    sitemap_url: 'https://neogenesis.app/sitemap.xml',
    repo_path: 'src/landing',
    deployment_provider: 'vercel',
    deployment_project_id_ref: 'vercel_project.neogenesis',
    expected_ga_measurement_id_ref: 'env.GA_MEASUREMENT_ID',
    ga4_source_key: 'NeoGenesis',
    ga4_property_kind: 'shared_host_filtered',
    posthog_capture_mode: 'expected',
    posthog_site_id: 'neogenesis',
    gsc_property_type: 'url_prefix',
    gsc_site_id: 'neogenesis',
    registry_sources: ['.agent/SSOT', 'scripts/ga4_traffic_report.py', 'scripts/sbu_gsc_all.mjs'],
    source_precedence: ['.agent/SSOT', 'sbus.ts', 'collector_config', 'README'],
    generated_from: 'owner_traffic_command.mjs',
    last_verified_at: null,
  },
  {
    id: 'toolpick',
    name: 'ToolPick',
    status: 'active_live',
    type: 'flagship_sbu',
    canonical_url: 'https://www.toolpick.dev',
    canonical_host: 'toolpick.dev',
    domain_aliases: ['toolpick.dev', 'www.toolpick.dev'],
    blog_url: 'https://www.toolpick.dev/blog',
    sitemap_url: 'https://www.toolpick.dev/sitemap.xml',
    repo_path: 'src/sbu/toolpick',
    deployment_provider: 'vercel',
    deployment_project_id_ref: 'vercel_project.toolpick',
    expected_ga_measurement_id_ref: 'env.GA_MEASUREMENT_ID',
    ga4_source_key: 'ToolPick',
    ga4_property_kind: 'dedicated',
    posthog_capture_mode: 'expected',
    posthog_site_id: 'toolpick',
    gsc_property_type: 'domain',
    gsc_site_id: 'toolpick',
    registry_sources: ['.agent/SSOT', 'scripts/sbu_gsc_all.mjs'],
    source_precedence: ['.agent/SSOT', 'sbus.ts', 'collector_config', 'README'],
    generated_from: 'owner_traffic_command.mjs',
    last_verified_at: null,
  },
  {
    id: 'ur-wrong',
    name: 'UR WRONG',
    status: 'active_live',
    type: 'ai_experience',
    canonical_url: 'https://ur-wrong.com',
    canonical_host: 'ur-wrong.com',
    domain_aliases: ['ur-wrong.com'],
    blog_url: 'https://ur-wrong.com/blog',
    sitemap_url: 'https://ur-wrong.com/sitemap.xml',
    repo_path: 'src/sbu/ur-wrong',
    deployment_provider: 'vercel',
    deployment_project_id_ref: 'vercel_project.ur_wrong',
    expected_ga_measurement_id_ref: 'env.GA_MEASUREMENT_ID',
    ga4_source_key: 'UR WRONG',
    ga4_property_kind: 'dedicated',
    posthog_capture_mode: 'expected',
    posthog_site_id: 'ur-wrong',
    gsc_property_type: 'url_prefix',
    gsc_site_id: 'ur-wrong',
    registry_sources: ['.agent/SSOT', 'scripts/sbu_gsc_all.mjs'],
    source_precedence: ['.agent/SSOT', 'sbus.ts', 'collector_config', 'README'],
    generated_from: 'owner_traffic_command.mjs',
    last_verified_at: null,
  },
  {
    id: 'reviewlab',
    name: 'ReviewLab',
    status: 'active_live',
    type: 'sbu',
    canonical_url: 'https://review.neogenesis.app',
    canonical_host: 'review.neogenesis.app',
    domain_aliases: ['review.neogenesis.app'],
    blog_url: 'https://review.neogenesis.app/posts',
    sitemap_url: 'https://review.neogenesis.app/sitemap.xml',
    repo_path: 'src/sbu/reviewlab',
    deployment_provider: 'vercel',
    deployment_project_id_ref: 'vercel_project.reviewlab',
    expected_ga_measurement_id_ref: 'env.GA_MEASUREMENT_ID',
    ga4_source_key: 'ReviewLab',
    ga4_property_kind: 'shared_host_filtered',
    posthog_capture_mode: 'site_id_or_host',
    posthog_site_id: 'reviewlab',
    gsc_property_type: 'url_prefix',
    gsc_site_id: 'reviewlab',
    registry_sources: ['.agent/SSOT', 'scripts/sbu_gsc_all.mjs', 'scripts/posthog_traffic.py'],
    source_precedence: ['.agent/SSOT', 'sbus.ts', 'collector_config', 'README'],
    generated_from: 'owner_traffic_command.mjs',
    last_verified_at: null,
  },
  {
    id: 'kott',
    name: 'K-OTT',
    status: 'active_live',
    type: 'sbu',
    canonical_url: 'https://kott.kr',
    canonical_host: 'kott.kr',
    domain_aliases: ['kott.kr'],
    blog_url: 'https://kott.kr/blog',
    sitemap_url: 'https://kott.kr/sitemap.xml',
    repo_path: 'src/sbu/k-ott',
    deployment_provider: 'vercel',
    deployment_project_id_ref: 'vercel_project.kott',
    expected_ga_measurement_id_ref: 'env.GA_MEASUREMENT_ID',
    ga4_source_key: 'K-OTT',
    ga4_property_kind: 'dedicated',
    posthog_capture_mode: 'site_id_or_host',
    posthog_site_id: 'kott',
    gsc_property_type: 'url_prefix',
    gsc_site_id: 'kott',
    registry_sources: ['.agent/SSOT', 'scripts/sbu_gsc_all.mjs', 'scripts/posthog_traffic.py'],
    source_precedence: ['.agent/SSOT', 'sbus.ts', 'collector_config', 'README'],
    generated_from: 'owner_traffic_command.mjs',
    last_verified_at: null,
  },
  {
    id: 'whylab',
    name: 'WhyLab',
    status: 'active_live',
    type: 'sbu',
    canonical_url: 'https://whylab.neogenesis.app',
    canonical_host: 'whylab.neogenesis.app',
    domain_aliases: ['whylab.neogenesis.app'],
    blog_url: 'https://whylab.neogenesis.app/blog',
    sitemap_url: 'https://whylab.neogenesis.app/sitemap.xml',
    repo_path: 'src/sbu/whylab',
    deployment_provider: 'vercel',
    deployment_project_id_ref: 'vercel_project.whylab',
    expected_ga_measurement_id_ref: 'env.GA_MEASUREMENT_ID',
    ga4_source_key: 'WhyLab',
    ga4_property_kind: 'shared_host_filtered',
    posthog_capture_mode: 'site_id_or_host',
    posthog_site_id: 'whylab',
    gsc_property_type: 'url_prefix',
    gsc_site_id: 'whylab',
    registry_sources: ['.agent/SSOT', 'scripts/sbu_gsc_all.mjs', 'scripts/posthog_traffic.py'],
    source_precedence: ['.agent/SSOT', 'sbus.ts', 'collector_config', 'README'],
    generated_from: 'owner_traffic_command.mjs',
    last_verified_at: null,
  },
  {
    id: 'ethicaai',
    name: 'EthicaAI',
    status: 'active_live',
    type: 'sbu',
    canonical_url: 'https://ethica.neogenesis.app',
    canonical_host: 'ethica.neogenesis.app',
    domain_aliases: ['ethica.neogenesis.app'],
    blog_url: 'https://ethica.neogenesis.app/blog',
    sitemap_url: 'https://ethica.neogenesis.app/sitemap.xml',
    repo_path: 'src/sbu/ethicaai',
    deployment_provider: 'vercel',
    deployment_project_id_ref: 'vercel_project.ethicaai',
    expected_ga_measurement_id_ref: 'env.GA_MEASUREMENT_ID',
    ga4_source_key: 'EthicaAI',
    ga4_property_kind: 'shared_host_filtered',
    posthog_capture_mode: 'site_id_or_host',
    posthog_site_id: 'ethicaai',
    gsc_property_type: 'url_prefix',
    gsc_site_id: 'ethicaai',
    registry_sources: ['.agent/SSOT', 'scripts/sbu_gsc_all.mjs', 'scripts/posthog_traffic.py'],
    source_precedence: ['.agent/SSOT', 'sbus.ts', 'collector_config', 'README'],
    generated_from: 'owner_traffic_command.mjs',
    last_verified_at: null,
  },
  {
    id: 'finstack',
    name: 'FinStack',
    status: 'active_live',
    type: 'sbu',
    canonical_url: 'https://finstack.neogenesis.app',
    canonical_host: 'finstack.neogenesis.app',
    domain_aliases: ['finstack.neogenesis.app'],
    blog_url: 'https://finstack.neogenesis.app/blog',
    sitemap_url: 'https://finstack.neogenesis.app/sitemap.xml',
    repo_path: 'src/sbu/finstack',
    deployment_provider: 'vercel',
    deployment_project_id_ref: 'vercel_project.finstack',
    expected_ga_measurement_id_ref: 'env.GA_MEASUREMENT_ID',
    ga4_source_key: 'FinStack',
    ga4_property_kind: 'shared_host_filtered',
    posthog_capture_mode: 'site_id_or_host',
    posthog_site_id: 'finstack',
    gsc_property_type: 'url_prefix',
    gsc_site_id: 'finstack',
    registry_sources: ['.agent/SSOT', 'scripts/sbu_gsc_all.mjs', 'scripts/posthog_traffic.py'],
    source_precedence: ['.agent/SSOT', 'sbus.ts', 'collector_config', 'README'],
    generated_from: 'owner_traffic_command.mjs',
    last_verified_at: null,
  },
  {
    id: 'aiforge',
    name: 'AIForge',
    status: 'active_live',
    type: 'sbu',
    canonical_url: 'https://aiforge.neogenesis.app',
    canonical_host: 'aiforge.neogenesis.app',
    domain_aliases: ['aiforge.neogenesis.app'],
    blog_url: 'https://aiforge.neogenesis.app/blog',
    sitemap_url: 'https://aiforge.neogenesis.app/sitemap.xml',
    repo_path: 'src/sbu/aiforge',
    deployment_provider: 'vercel',
    deployment_project_id_ref: 'vercel_project.aiforge',
    expected_ga_measurement_id_ref: 'env.GA_MEASUREMENT_ID',
    ga4_source_key: 'AIForge',
    ga4_property_kind: 'shared_host_filtered',
    posthog_capture_mode: 'site_id_or_host',
    posthog_site_id: 'aiforge',
    gsc_property_type: 'url_prefix',
    gsc_site_id: 'aiforge',
    registry_sources: ['.agent/SSOT', 'scripts/sbu_gsc_all.mjs', 'scripts/posthog_traffic.py'],
    source_precedence: ['.agent/SSOT', 'sbus.ts', 'collector_config', 'README'],
    generated_from: 'owner_traffic_command.mjs',
    last_verified_at: null,
  },
  {
    id: 'sellkit',
    name: 'SellKit',
    status: 'active_live',
    type: 'sbu',
    canonical_url: 'https://sellkit.neogenesis.app',
    canonical_host: 'sellkit.neogenesis.app',
    domain_aliases: ['sellkit.neogenesis.app'],
    blog_url: 'https://sellkit.neogenesis.app/blog',
    sitemap_url: 'https://sellkit.neogenesis.app/sitemap.xml',
    repo_path: 'src/sbu/sellkit',
    deployment_provider: 'vercel',
    deployment_project_id_ref: 'vercel_project.sellkit',
    expected_ga_measurement_id_ref: 'env.GA_MEASUREMENT_ID',
    ga4_source_key: 'SellKit',
    ga4_property_kind: 'shared_host_filtered',
    posthog_capture_mode: 'site_id_or_host',
    posthog_site_id: 'sellkit',
    gsc_property_type: 'url_prefix',
    gsc_site_id: 'sellkit',
    registry_sources: ['.agent/SSOT', 'scripts/sbu_gsc_all.mjs', 'scripts/posthog_traffic.py'],
    source_precedence: ['.agent/SSOT', 'sbus.ts', 'collector_config', 'README'],
    generated_from: 'owner_traffic_command.mjs',
    last_verified_at: null,
  },
  {
    id: 'deploystack',
    name: 'DeployStack',
    status: 'active_live',
    type: 'sbu',
    canonical_url: 'https://deploystack.neogenesis.app',
    canonical_host: 'deploystack.neogenesis.app',
    domain_aliases: ['deploystack.neogenesis.app'],
    blog_url: 'https://deploystack.neogenesis.app/blog',
    sitemap_url: 'https://deploystack.neogenesis.app/sitemap.xml',
    repo_path: 'src/sbu/deploystack',
    deployment_provider: 'vercel',
    deployment_project_id_ref: 'vercel_project.deploystack',
    expected_ga_measurement_id_ref: 'env.GA_MEASUREMENT_ID',
    ga4_source_key: 'DeployStack',
    ga4_property_kind: 'shared_host_filtered',
    posthog_capture_mode: 'site_id_or_host',
    posthog_site_id: 'deploystack',
    gsc_property_type: 'url_prefix',
    gsc_site_id: 'deploystack',
    registry_sources: ['.agent/SSOT', 'scripts/sbu_gsc_all.mjs', 'scripts/posthog_traffic.py'],
    source_precedence: ['.agent/SSOT', 'sbus.ts', 'collector_config', 'README'],
    generated_from: 'owner_traffic_command.mjs',
    last_verified_at: null,
  },
  {
    id: 'craftdesk',
    name: 'CraftDesk',
    status: 'active_live',
    type: 'sbu',
    canonical_url: 'https://craftdesk.neogenesis.app',
    canonical_host: 'craftdesk.neogenesis.app',
    domain_aliases: ['craftdesk.neogenesis.app'],
    blog_url: 'https://craftdesk.neogenesis.app/blog',
    sitemap_url: 'https://craftdesk.neogenesis.app/sitemap.xml',
    repo_path: 'src/sbu/craftdesk',
    deployment_provider: 'vercel',
    deployment_project_id_ref: 'vercel_project.craftdesk',
    expected_ga_measurement_id_ref: 'env.GA_MEASUREMENT_ID',
    ga4_source_key: 'CraftDesk',
    ga4_property_kind: 'shared_host_filtered',
    posthog_capture_mode: 'site_id_or_host',
    posthog_site_id: 'craftdesk',
    gsc_property_type: 'url_prefix',
    gsc_site_id: 'craftdesk',
    registry_sources: ['.agent/SSOT', 'scripts/sbu_gsc_all.mjs', 'scripts/posthog_traffic.py'],
    source_precedence: ['.agent/SSOT', 'sbus.ts', 'collector_config', 'README'],
    generated_from: 'owner_traffic_command.mjs',
    last_verified_at: null,
  },
  {
    id: 'heoyesol',
    name: 'HeoYesol Portfolio',
    status: 'active_live',
    type: 'portfolio',
    canonical_url: 'https://heoyesol.kr',
    canonical_host: 'heoyesol.kr',
    domain_aliases: ['heoyesol.kr', 'www.heoyesol.kr'],
    blog_url: null,
    sitemap_url: 'https://heoyesol.kr/sitemap.xml',
    repo_path: '..\\portfolio',
    deployment_provider: 'github_pages_or_vercel',
    deployment_project_id_ref: 'deployment_project.heoyesol',
    expected_ga_measurement_id_ref: 'env.GA_MEASUREMENT_ID',
    ga4_source_key: 'HeoYesol Portfolio',
    ga4_property_kind: 'dedicated',
    posthog_capture_mode: 'not_configured',
    posthog_site_id: 'heoyesol',
    gsc_property_type: 'domain',
    gsc_site_id: 'heoyesol',
    registry_sources: ['.agent/SSOT', 'logs/ga4_result.json', 'scripts/sbu_gsc_all.mjs'],
    source_precedence: ['.agent/SSOT', 'sbus.ts', 'collector_config', 'README'],
    generated_from: 'owner_traffic_command.mjs',
    last_verified_at: null,
  },
  {
    id: 'koreanllm',
    name: 'KoreanLLM',
    status: 'candidate_decision',
    type: 'candidate_site',
    canonical_url: null,
    canonical_host: null,
    domain_aliases: [],
    blog_url: null,
    sitemap_url: null,
    repo_path: null,
    deployment_provider: 'unknown',
    deployment_project_id_ref: null,
    expected_ga_measurement_id_ref: null,
    ga4_source_key: null,
    ga4_property_kind: 'none',
    posthog_capture_mode: 'none',
    posthog_site_id: null,
    gsc_property_type: 'none',
    gsc_site_id: null,
    registry_sources: ['owner_request_candidate'],
    source_precedence: ['.agent/SSOT', 'sbus.ts', 'collector_config', 'README'],
    generated_from: 'owner_traffic_command.mjs',
    last_verified_at: null,
  },
];

function kstNow() {
  return new Date(Date.now() + KST_OFFSET_MS).toISOString().replace('Z', '+09:00');
}

function kstFromMs(ms) {
  return new Date(ms + KST_OFFSET_MS).toISOString().replace('Z', '+09:00');
}

function stableId(prefix, seed) {
  const hash = crypto.createHash('sha256').update(seed).digest('hex').slice(0, 12);
  return `${prefix}_${hash}`;
}

function safeReadJson(filePath) {
  try {
    if (!fs.existsSync(filePath)) return { ok: false, error: 'missing', json: null };
    const stat = fs.statSync(filePath);
    return { ok: true, error: null, json: JSON.parse(fs.readFileSync(filePath, 'utf8')), mtime_ms: stat.mtimeMs };
  } catch (error) {
    return { ok: false, error: error.message, json: null };
  }
}

function atomicWriteJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const tmpPath = `${filePath}.${process.pid}.tmp`;
  fs.writeFileSync(tmpPath, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  fs.renameSync(tmpPath, filePath);
}

function secondsSince(value) {
  if (!value) return null;
  const parsed = new Date(value).getTime();
  if (!Number.isFinite(parsed)) return null;
  return Math.max(0, Math.round((Date.now() - parsed) / 1000));
}

function rel(filePath) {
  return path.relative(ROOT, filePath);
}

function asNumber(value) {
  const numeric = Number(value ?? 0);
  return Number.isFinite(numeric) ? numeric : 0;
}

function optionalNumber(value) {
  if (value === null || value === undefined || value === '') return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function hasSourceConflict(primaryValue, secondaryValue) {
  if (!Number.isFinite(primaryValue) || !Number.isFinite(secondaryValue)) return false;
  if (primaryValue <= 0 || secondaryValue <= 0) return false;
  const high = Math.max(primaryValue, secondaryValue);
  const low = Math.min(primaryValue, secondaryValue);
  return high >= 20 && (high - low) / high >= 0.5;
}

function kstDateKey(offsetDays = 0) {
  return new Date(Date.now() + KST_OFFSET_MS - offsetDays * DAY_MS).toISOString().slice(0, 10);
}

function dailySum(daily, startOffset, days, field) {
  if (!Array.isArray(daily)) return null;
  let found = false;
  let sum = 0;
  const wanted = new Set(Array.from({ length: days }, (_item, index) => kstDateKey(startOffset + index)));
  for (const row of daily) {
    if (!wanted.has(String(row.date))) continue;
    found = true;
    sum += asNumber(row[field]);
  }
  return found ? sum : null;
}

function deltaPct(current, previous) {
  if (!Number.isFinite(current) || !Number.isFinite(previous) || previous <= 0) return null;
  return (current - previous) / previous;
}

function rate(numerator, denominator) {
  if (!Number.isFinite(numerator) || !Number.isFinite(denominator) || denominator <= 0) return null;
  return numerator / denominator;
}

function clamp(value, min = 0, max = 100) {
  return Math.max(min, Math.min(max, value));
}

function scoreLog(value, reference) {
  if (value <= 0) return 0;
  return clamp((Math.log10(value + 1) / Math.log10(reference + 1)) * 100);
}

function containsMojibake(value) {
  if (typeof value !== 'string') return false;
  return /\uFFFD/.test(value) || /\?[ㄱ-ㅎㅏ-ㅣ가-힣]/.test(value) || /[ㄱ-ㅎㅏ-ㅣ가-힣]\?/.test(value);
}

function findMojibakeSamples(value, samples = []) {
  if (samples.length >= 3) return samples;
  if (typeof value === 'string') {
    if (containsMojibake(value)) samples.push(value.slice(0, 160));
    return samples;
  }
  if (Array.isArray(value)) {
    for (const item of value) findMojibakeSamples(item, samples);
    return samples;
  }
  if (value && typeof value === 'object') {
    for (const item of Object.values(value)) findMojibakeSamples(item, samples);
  }
  return samples;
}

function readGscBySite() {
  if (!fs.existsSync(GROWTH_DIR)) return { files: [], bySite: new Map() };
  const files = fs
    .readdirSync(GROWTH_DIR)
    .filter((name) => /^gsc-all-sbu.*\.json$/.test(name))
    .map((name) => path.join(GROWTH_DIR, name))
    .sort((a, b) => fs.statSync(b).mtimeMs - fs.statSync(a).mtimeMs);
  const bySite = new Map();
  const fileRuns = new Map();
  const usedPaths = new Set();
  for (const filePath of files) {
    const loaded = safeReadJson(filePath);
    if (!loaded.ok || !loaded.json) continue;
    const json = loaded.json;
    const relativePath = rel(filePath);
    fileRuns.set(relativePath, {
      source: 'gsc',
      path: relativePath,
      ok: true,
      generated_at: json.generatedAt ?? null,
      sites: Array.isArray(json.sites) ? json.sites.length : 0,
      stale_seconds: secondsSince(json.generatedAt),
    });
    for (const site of json.sites ?? []) {
      if (!site?.id || bySite.has(site.id)) continue;
      bySite.set(site.id, { ...site, _sourceGeneratedAt: json.generatedAt ?? null, _sourcePath: relativePath });
      usedPaths.add(relativePath);
    }
  }
  return { files: Array.from(usedPaths).map((relativePath) => fileRuns.get(relativePath)).filter(Boolean), bySite };
}

function buildSources() {
  const ga4Path = path.join(ROOT, 'logs', 'ga4_result.json');
  const posthogPath = path.join(GROWTH_DIR, 'posthog-traffic-latest.json');
  const acquisitionPath = path.join(GROWTH_DIR, 'acquisition-dashboard-latest.json');
  const liveProbePath = path.join(OUT_DIR, 'live-tag-probe-latest.json');
  const ga4 = safeReadJson(ga4Path);
  const posthog = safeReadJson(posthogPath);
  const acquisition = safeReadJson(acquisitionPath);
  const liveProbe = safeReadJson(liveProbePath);
  const gsc = readGscBySite();

  const sourceRuns = [
    {
      source: 'ga4',
      path: rel(ga4Path),
      ok: ga4.ok,
      generated_at: ga4.json?.generatedAt ?? (ga4.mtime_ms ? kstFromMs(ga4.mtime_ms) : null),
      rows: ga4.ok ? Object.keys(ga4.json ?? {}).filter((key) => !key.startsWith('_')).length : 0,
      stale_seconds: secondsSince(ga4.json?.generatedAt ?? (ga4.mtime_ms ? kstFromMs(ga4.mtime_ms) : null)),
      error: ga4.ok ? null : ga4.error,
    },
    {
      source: 'posthog',
      path: rel(posthogPath),
      ok: posthog.ok,
      generated_at: posthog.json?.generatedAt ?? (posthog.mtime_ms ? kstFromMs(posthog.mtime_ms) : null),
      days: posthog.json?.days ?? null,
      rows: Array.isArray(posthog.json?.rows) ? posthog.json.rows.length : 0,
      stale_seconds: secondsSince(posthog.json?.generatedAt ?? (posthog.mtime_ms ? kstFromMs(posthog.mtime_ms) : null)),
      error: posthog.ok ? null : posthog.error,
    },
    {
      source: 'live_tag_probe',
      path: rel(liveProbePath),
      ok: liveProbe.ok,
      generated_at: liveProbe.json?.generatedAt ?? (liveProbe.mtime_ms ? kstFromMs(liveProbe.mtime_ms) : null),
      rows: Array.isArray(liveProbe.json?.sites) ? liveProbe.json.sites.length : 0,
      stale_seconds: secondsSince(liveProbe.json?.generatedAt ?? (liveProbe.mtime_ms ? kstFromMs(liveProbe.mtime_ms) : null)),
      error: liveProbe.ok ? null : liveProbe.error,
    },
    {
      source: 'acquisition_model',
      path: rel(acquisitionPath),
      ok: acquisition.ok,
      generated_at: acquisition.json?.generatedAt ?? null,
      rows: Array.isArray(acquisition.json?.rows) ? acquisition.json.rows.length : 0,
      stale_seconds: secondsSince(acquisition.json?.generatedAt),
      error: acquisition.ok ? null : acquisition.error,
    },
    ...gsc.files.slice(0, 5),
  ];

  return {
    ga4: ga4.json ?? {},
    posthog: posthog.json ?? {},
    acquisition: acquisition.json ?? {},
    liveProbe: liveProbe.json ?? {},
    gscBySite: gsc.bySite,
    sourceRuns,
    sourceErrors: sourceRuns
      .filter((source) => !source.ok)
      .map((source) => ({ source: source.source, path: source.path, error: source.error ?? 'unavailable' })),
  };
}

function getPosthogRow(source, site) {
  const rows = source.posthog?.rows ?? [];
  return rows.find((row) => row.site === site.posthog_site_id || row.site === site.id) ?? null;
}

function getAcquisitionRow(source, site) {
  const rows = source.acquisition?.rows ?? [];
  return rows.find((row) => row.site === site.id) ?? null;
}

function getLiveProbeRow(source, site) {
  const rows = source.liveProbe?.sites ?? [];
  return rows.find((row) => row.site_id === site.id) ?? null;
}

function summarizeGsc(siteData) {
  if (!siteData) return null;
  const opportunities = siteData.opportunities ?? [];
  const opportunityImpressions = opportunities.reduce((sum, item) => sum + asNumber(item.impressions), 0);
  const opportunityClicks = opportunities.reduce((sum, item) => sum + asNumber(item.clicks), 0);
  const top = opportunities[0] ?? null;
  const topQuery = top?.topQuery ?? top?.queries?.[0]?.query ?? null;
  return {
    property_listed: Boolean(siteData.propertyListed),
    permission: siteData.permission ?? null,
    sitemap_known: Boolean(siteData.gscSitemap?.known ?? siteData.gscSitemap?.ok),
    live_sitemap_ok: Boolean(siteData.liveSitemap?.ok),
    live_sitemap_status: siteData.liveSitemap?.status ?? null,
    live_sitemap_loc_count: siteData.liveSitemap?.locCount ?? null,
    search_analytics_ok: Boolean(siteData.searchAnalytics?.ok),
    search_analytics_rows: asNumber(siteData.searchAnalytics?.rows),
    opportunity_count: opportunities.length,
    opportunity_impressions: opportunityImpressions,
    opportunity_clicks: opportunityClicks,
    top_opportunity: top
      ? {
          page: top.page,
          impressions: asNumber(top.impressions),
          clicks: asNumber(top.clicks),
          average_position: asNumber(top.averagePosition),
          top_query: topQuery,
        }
      : null,
    source_generated_at: siteData._sourceGeneratedAt ?? null,
    source_path: siteData._sourcePath ?? null,
    mojibake_samples: findMojibakeSamples(opportunities),
  };
}

function buildPerformance(site, ga4, posthog) {
  const posthogDaily = posthog?.daily ?? [];
  const todayFromPosthog = dailySum(posthogDaily, 0, 1, 'users');
  const yesterdayFromPosthog = dailySum(posthogDaily, 1, 1, 'users');
  const todayVisitors = todayFromPosthog ?? ga4?.users_today ?? 0;
  const yesterdayVisitors = yesterdayFromPosthog ?? null;
  const posthogVisitors7d = optionalNumber(posthog?.users);
  const ga4Visitors7d = optionalNumber(ga4?.users_7d);
  const visitors7d = posthogVisitors7d ?? ga4Visitors7d ?? 0;
  const visitorsPrevious7d = posthog?.previous_users ?? null;
  const posthogPageviews7d = optionalNumber(posthog?.pageviews);
  const ga4Pageviews7d = optionalNumber(ga4?.views_7d);
  const pageviews7d = posthogPageviews7d ?? ga4Pageviews7d ?? 0;
  const pageviewsPrevious7d = posthog?.previous_pageviews ?? null;
  const decisionEvents7d = posthog?.decision_events ?? 0;
  const decisionEventsPrevious7d = posthog?.previous_decision_events ?? null;
  const visitorsDeltaPct = visitorsPrevious7d === null ? null : deltaPct(visitors7d, visitorsPrevious7d);
  const pageviewsDeltaPct = pageviewsPrevious7d === null ? null : deltaPct(pageviews7d, pageviewsPrevious7d);
  const decisionDeltaPct = decisionEventsPrevious7d === null ? null : deltaPct(decisionEvents7d, decisionEventsPrevious7d);
  const decisionRate7d = rate(decisionEvents7d, pageviews7d);
  const ga4WindowUsers = (ga4?.users_7d ?? 0) + (ga4?.users_today ?? 0);
  const primarySource = posthog ? 'posthog' : ga4 ? 'ga4' : 'none';
  const sourceConflict = hasSourceConflict(posthogVisitors7d, ga4Visitors7d);
  const ga4MissingDespitePosthog = posthog && ga4 && visitors7d >= 5 && pageviews7d >= 10 && ga4WindowUsers === 0;
  const trustState = primarySource === 'none' || ga4MissingDespitePosthog || sourceConflict ? 'degraded' : 'trusted';
  const signals = [];
  if (site.status === 'active_live') {
    if (visitorsDeltaPct !== null && visitorsDeltaPct <= -0.25) signals.push('traffic_drop');
    if (visitors7d >= 20 && decisionEvents7d === 0) signals.push('conversion_leak');
  }

  let stage = 'no_traffic';
  let primaryIssue = '최근 방문자 신호가 약합니다.';
  let nextAction = `${site.name}의 배포/인덱싱/유입 경로를 확인합니다.`;

  if (site.status !== 'active_live') {
    stage = 'candidate';
    primaryIssue = '아직 라이브 운영 대상이 아닙니다.';
    nextAction = '라이브 후보로 유지할지 결정합니다.';
  } else if (signals.includes('traffic_drop')) {
    stage = 'traffic_drop';
    primaryIssue = '전주 대비 방문자가 크게 줄었습니다.';
    nextAction = `${site.name}의 최근 배포, 색인, 주요 유입 페이지를 확인합니다.`;
  } else if (signals.includes('conversion_leak')) {
    stage = 'conversion_leak';
    primaryIssue = '방문자는 있지만 성과 이벤트가 없습니다.';
    nextAction = `${site.name}의 상위 유입 페이지에 CTA와 decision event를 심습니다.`;
  } else if (visitorsDeltaPct !== null && visitorsDeltaPct >= 0.25 && visitors7d >= 10) {
    stage = 'growing';
    primaryIssue = '전주 대비 방문자가 늘고 있습니다.';
    nextAction = `${site.name}의 성장 페이지를 확장하고 전환 경로를 강화합니다.`;
  } else if (visitors7d >= 20 && decisionEvents7d > 0) {
    stage = 'performing';
    primaryIssue = '방문과 성과 이벤트가 모두 잡힙니다.';
    nextAction = `${site.name}의 성과 이벤트 발생 페이지를 복제/확장합니다.`;
  } else if (visitors7d > 0) {
    stage = 'early_signal';
    primaryIssue = '작은 방문자 신호가 있습니다.';
    nextAction = `${site.name}에 작은 배포/콘텐츠 실험을 1개만 추가합니다.`;
  }

  return {
    primary_source: primarySource,
    trust_state: trustState,
    posthog_visitors_7d: posthogVisitors7d,
    ga4_visitors_7d: ga4Visitors7d,
    source_conflict: sourceConflict,
    today_visitors: todayVisitors,
    yesterday_visitors: yesterdayVisitors,
    visitors_7d: visitors7d,
    visitors_prev_7d: visitorsPrevious7d,
    visitors_delta_pct: visitorsDeltaPct,
    pageviews_7d: pageviews7d,
    pageviews_prev_7d: pageviewsPrevious7d,
    pageviews_delta_pct: pageviewsDeltaPct,
    decision_events_7d: decisionEvents7d,
    decision_events_prev_7d: decisionEventsPrevious7d,
    decision_delta_pct: decisionDeltaPct,
    decision_rate_7d: decisionRate7d,
    signals,
    stage,
    primary_issue: primaryIssue,
    next_action: nextAction,
  };
}

function buildSiteRow(site, sources) {
  const ga4Raw = site.ga4_source_key ? sources.ga4?.[site.ga4_source_key] : null;
  const posthogRaw = getPosthogRow(sources, site);
  const gscRaw = site.gsc_site_id ? sources.gscBySite.get(site.gsc_site_id) : null;
  const acquisitionRaw = getAcquisitionRow(sources, site);
  const liveRaw = getLiveProbeRow(sources, site);
  const gsc = summarizeGsc(gscRaw);

  const posthog = posthogRaw
    ? {
        events: asNumber(posthogRaw.events),
        pageviews: asNumber(posthogRaw.pageviews),
        users: asNumber(posthogRaw.users),
        decision_events: posthogRaw.decisionEvents === undefined ? null : asNumber(posthogRaw.decisionEvents),
        legacy_action_events: asNumber(posthogRaw.legacyActionEvents ?? posthogRaw.actionEvents),
        last_seen: posthogRaw.lastSeen ?? null,
        previous_events: optionalNumber(posthogRaw.previousEvents),
        previous_pageviews: optionalNumber(posthogRaw.previousPageviews),
        previous_decision_events: optionalNumber(posthogRaw.previousDecisionEvents),
        previous_users: optionalNumber(posthogRaw.previousUsers),
        daily: Array.isArray(posthogRaw.daily)
          ? posthogRaw.daily.map((row) => ({
              date: String(row.date ?? ''),
              events: asNumber(row.events),
              pageviews: asNumber(row.pageviews),
              decision_events: asNumber(row.decisionEvents),
              legacy_action_events: asNumber(row.legacyActionEvents),
              users: asNumber(row.users),
              last_seen: row.lastSeen ?? null,
            }))
          : [],
      }
    : null;

  const ga4 = ga4Raw
    ? {
        users_7d: asNumber(ga4Raw.users_7d),
        views_7d: asNumber(ga4Raw.views_7d),
        sessions_7d: asNumber(ga4Raw.sessions_7d),
        users_28d: asNumber(ga4Raw.users_28d),
        views_28d: asNumber(ga4Raw.views_28d),
        sessions_28d: asNumber(ga4Raw.sessions_28d),
        users_today: asNumber(ga4Raw.users_today),
        property_kind: site.ga4_property_kind,
        host_filter: ga4Raw.host ?? null,
      }
    : null;

  const performance = buildPerformance(site, ga4, posthog);

  const measurement = {
    registry: true,
    ga4_mapping: Boolean(site.ga4_source_key),
    ga4_latest: Boolean(ga4),
    posthog_mapping: site.posthog_capture_mode !== 'none' && site.posthog_capture_mode !== 'not_configured',
    posthog_latest: Boolean(posthog),
    posthog_explicitly_not_configured: site.posthog_capture_mode === 'not_configured',
    gsc_mapping: Boolean(site.gsc_site_id),
    gsc_latest: Boolean(gsc),
    live_sitemap_latest: Boolean(gsc?.live_sitemap_ok),
  };

  const demandScore = scoreLog((gsc?.opportunity_impressions ?? 0) + (gsc?.opportunity_clicks ?? 0) * 20, 350);
  const trafficScore = scoreLog((posthog?.users ?? 0) + (ga4?.users_7d ?? 0) + (posthog?.pageviews ?? 0) * 0.2, 120);
  const conversionScore = posthog?.decision_events === null ? null : scoreLog(posthog?.decision_events ?? 0, 30);
  const modelScore = asNumber(acquisitionRaw?.score);

  return {
    id: site.id,
    name: site.name,
    status: site.status,
    type: site.type,
    canonical_url: site.canonical_url,
    canonical_host: site.canonical_host,
    repo_path: site.repo_path,
    data: {
      ga4,
      posthog,
      gsc,
      live: liveRaw
        ? {
            ok: Boolean(liveRaw.ok),
            status: liveRaw.status ?? null,
            ga4_tag_present: Boolean(liveRaw.ga4?.has_tag),
            ga4_measurement_ids: liveRaw.ga4?.measurement_ids ?? [],
            posthog_tag_present: Boolean(liveRaw.posthog?.has_tag),
            html_bytes: liveRaw.html_bytes ?? 0,
          }
        : null,
      acquisition_model: acquisitionRaw
        ? {
            stage: acquisitionRaw.stage ?? null,
            score: modelScore,
            strategy: acquisitionRaw.strategy ?? [],
            measurement_warnings: acquisitionRaw.measurementWarnings ?? [],
          }
        : null,
    },
    performance,
    measurement,
    score_components: {
      demand: Math.round(demandScore * 10) / 10,
      traffic: Math.round(trafficScore * 10) / 10,
      conversion: conversionScore === null ? null : Math.round(conversionScore * 10) / 10,
      modeled: modelScore || null,
    },
    owner_score: Math.round(clamp(demandScore * 0.45 + trafficScore * 0.4 + (conversionScore ?? 20) * 0.15) * 10) / 10,
    blocked_by_measurement: false,
  };
}

function finding(id, site, severity, title, evidence, action = null) {
  return {
    id: stableId('finding', `${id}:${site?.id ?? 'source'}:${JSON.stringify(evidence)}`),
    code: id,
    severity,
    site_id: site?.id ?? null,
    site_name: site?.name ?? null,
    title,
    evidence,
    recommended_action: action,
  };
}

function buildFindings(siteRows) {
  const findings = [];
  for (const row of siteRows) {
    const site = { id: row.id, name: row.name };
    const ph = row.data.posthog;
    const ga4 = row.data.ga4;
    const gsc = row.data.gsc;
    const live = row.data.live;

    if (row.status === 'candidate_decision') {
      findings.push(
        finding('SITE_CANDIDATE_UNDECIDED', site, 'P3', 'Candidate site is visible but not counted as active live traffic.', {
          status: row.status,
        }, 'Decide whether to promote, exclude, or archive this site.')
      );
      continue;
    }

    for (const [key, enabled] of Object.entries(row.measurement)) {
      if (key === 'posthog_explicitly_not_configured') continue;
      if (enabled) continue;
      if (key.startsWith('posthog_') && row.measurement.posthog_explicitly_not_configured) continue;
      const severity = key.endsWith('_latest') ? 'P2' : 'P1';
      findings.push(
        finding('COVERAGE_MAPPING_MISSING', site, severity, `Missing source coverage: ${key}`, {
          coverage_key: key,
          canonical_host: row.canonical_host,
        }, 'Add or explicitly exclude this source in the site registry and coverage matrix.')
      );
    }

    if (row.measurement.posthog_explicitly_not_configured) {
      findings.push(
        finding('POSTHOG_EXPLICITLY_NOT_CONFIGURED', site, 'P3', 'PostHog is explicitly not configured for this site.', {
          posthog_capture_mode: 'not_configured',
        }, 'Use GA4 and GSC for this site unless product behavior analytics becomes necessary.')
      );
    }

    const ga4CurrentWindowUsers = (ga4?.users_7d ?? 0) + (ga4?.users_today ?? 0);
    if (ph && ga4 && ph.users >= 5 && ph.pageviews >= 10 && ga4CurrentWindowUsers === 0) {
      if (live?.ga4_tag_present) {
        findings.push(
          finding('GA4_COLLECTION_LAG_OR_BLOCKED', site, 'P2', 'GA4 tag is present but GA4 current-window users are still zero while PostHog has traffic.', {
            posthog_users_7d: ph.users,
            posthog_pageviews_7d: ph.pageviews,
            ga4_users_7d: ga4.users_7d,
            ga4_users_today: ga4.users_today,
            ga4_measurement_ids: live.ga4_measurement_ids,
            host_filter: ga4.host_filter,
          }, 'Keep the site visible, then recheck GA4 after data latency; if it remains zero, inspect ad blockers, consent, and duplicate static analytics.')
        );
      } else {
        findings.push(
          finding('GA4_TAG_MISSING', site, 'P1', 'PostHog has traffic but no GA4 tag was found in the live HTML.', {
            posthog_users_7d: ph.users,
            posthog_pageviews_7d: ph.pageviews,
            ga4_users_7d: ga4.users_7d,
            ga4_users_today: ga4.users_today,
            host_filter: ga4.host_filter,
          }, 'Add the shared GA4 tag or repair the production environment variable before trusting acquisition metrics.')
        );
      }
    } else if (ph && ga4 && ph.users >= 5 && ph.pageviews >= 10 && ga4.users_7d === 0 && ga4.users_today > 0) {
      findings.push(
        finding('GA4_WINDOW_MISMATCH', site, 'P3', 'PostHog recent traffic overlaps with GA4 today, while the GA4 7d-yesterday window is zero.', {
          posthog_users_7d: ph.users,
          posthog_pageviews_7d: ph.pageviews,
          ga4_users_7d: ga4.users_7d,
          ga4_users_today: ga4.users_today,
          ga4_property_kind: ga4.property_kind,
          host_filter: ga4.host_filter,
        }, 'Use GA4 today plus 7d-yesterday for live monitoring, and compare strict calendar windows only in diagnostics.')
      );
    }

    if (ph && ph.decision_events === null && ph.legacy_action_events > 0) {
      findings.push(
        finding('POSTHOG_DECISION_EVENT_UNAVAILABLE', site, 'P1', 'PostHog action count is legacy non-pageview traffic, not an allowlisted decision metric.', {
          legacy_action_events: ph.legacy_action_events,
          pageviews: ph.pageviews,
        }, 'Rerun PostHog collection with decision_event_allowlist.json and treat legacy actions as diagnostic only.')
      );
    }

    if (ph && ph.decision_events === 0 && ph.pageviews >= 20) {
      findings.push(
        finding('POSTHOG_DECISION_EVENT_ZERO', site, 'P2', 'Traffic exists but no allowlisted decision event was captured.', {
          pageviews: ph.pageviews,
          decision_events: ph.decision_events,
        }, 'Instrument one primary owner decision event for this site before optimizing conversion.')
      );
    }

    if (ph && ph.decision_events !== null && ph.decision_events > 0 && ph.legacy_action_events >= ph.decision_events * 5) {
      findings.push(
        finding('POSTHOG_NOISE_SUSPECTED', site, 'P2', 'Broad non-pageview activity is much larger than allowlisted decision events.', {
          legacy_action_events: ph.legacy_action_events,
          decision_events: ph.decision_events,
        }, 'Keep noisy PostHog events out of owner KPI cards and expose them only in diagnostics.')
      );
    }

    if (gsc?.source_generated_at) {
      findings.push(
        finding('GSC_DELAYED_DATA', site, 'P3', 'Search Console data is delayed by design and should not be read as live traffic.', {
          source_generated_at: gsc.source_generated_at,
          source_path: gsc.source_path,
        }, 'Use GSC for search demand/opportunity, not same-day live decisions.')
      );
    }

    if (gsc && gsc.property_listed && gsc.search_analytics_ok && gsc.search_analytics_rows === 0) {
      findings.push(
        finding('GSC_PARTIAL_DETAIL_DATA', site, 'P2', 'GSC property is available but detailed search rows are empty for the current window.', {
          property_listed: gsc.property_listed,
          sitemap_known: gsc.sitemap_known,
          search_analytics_rows: gsc.search_analytics_rows,
        }, 'Keep the site visible, but do not infer that search demand is zero without a wider window.')
      );
    }

    if (gsc?.mojibake_samples?.length) {
      findings.push(
        finding('GSC_UTF8_BROKEN', site, 'P1', 'Korean search text appears mojibake-encoded in GSC-derived output.', {
          samples: gsc.mojibake_samples,
        }, 'Fix UTF-8 handling in downstream reports before showing Korean query strings in the owner dashboard.')
      );
    }
  }
  return findings;
}

function applyMeasurementBlocks(siteRows, findings) {
  const blockingCodes = new Set(['COVERAGE_MAPPING_MISSING', 'GA4_TAG_MISSING', 'POSTHOG_DECISION_EVENT_UNAVAILABLE', 'GSC_UTF8_BROKEN']);
  const blockedSites = new Set(
    findings
      .filter((item) => ['P0', 'P1'].includes(item.severity) && blockingCodes.has(item.code) && item.site_id)
      .map((item) => item.site_id)
  );
  return siteRows.map((row) => ({
    ...row,
    blocked_by_measurement: blockedSites.has(row.id),
  }));
}

function buildActions(siteRows, findings) {
  const actions = [];
  const pushAction = (site, priority, action_class, title, rationale, source, impact = null) => {
    actions.push({
      id: stableId('action', `${site.id}:${action_class}:${title}`),
      priority,
      impact: impact ?? asNumber(site.performance?.visitors_7d),
      site_id: site.id,
      site_name: site.name,
      action_class,
      title,
      rationale,
      source,
    });
  };

  const measurementGroups = new Map();
  for (const item of findings.filter((entry) => ['P0', 'P1'].includes(entry.severity))) {
    if (!item.site_id) continue;
    if (!measurementGroups.has(item.site_id)) measurementGroups.set(item.site_id, []);
    measurementGroups.get(item.site_id).push(item);
  }

  for (const [siteId, group] of measurementGroups.entries()) {
    const site = siteRows.find((row) => row.id === siteId);
    if (!site) continue;
    const priority = group.some((entry) => entry.severity === 'P0') ? 1 : 2;
    const codes = Array.from(new Set(group.map((entry) => entry.code))).join(', ');
    const rationale = Array.from(new Set(group.map((entry) => entry.recommended_action).filter(Boolean))).join(' ');
    pushAction(
      site,
      priority,
      'FIX_MEASUREMENT',
      `Fix tracking integrity before trusting ${site.name}.`,
      rationale,
      codes
    );
  }

  for (const site of siteRows.filter((row) => row.status === 'active_live' && !row.blocked_by_measurement)) {
    const gsc = site.data.gsc;
    const ph = site.data.posthog;
    const performance = site.performance ?? {};
    const signals = new Set(Array.isArray(performance.signals) ? performance.signals : [performance.stage].filter(Boolean));
    let pushedPerformanceAction = false;
    if (signals.has('traffic_drop')) {
      pushAction(
        site,
        3,
        'RECOVER_TRAFFIC',
        performance.next_action,
        `${site.name} visitors moved ${Math.round(asNumber(performance.visitors_delta_pct) * 1000) / 10}% versus the previous 7d window.`,
        'performance',
        asNumber(performance.visitors_7d)
      );
      pushedPerformanceAction = true;
    }
    if (signals.has('conversion_leak')) {
      pushAction(
        site,
        3,
        'IMPROVE_CONVERSION',
        performance.next_action,
        `${performance.visitors_7d} visitors and ${performance.pageviews_7d} pageviews produced ${performance.decision_events_7d} decision events in the latest 7d window.`,
        'performance',
        asNumber(performance.visitors_7d)
      );
      pushedPerformanceAction = true;
    }
    if (pushedPerformanceAction) {
      continue;
    }
    if (gsc?.top_opportunity && gsc.opportunity_impressions >= 10) {
      pushAction(
        site,
        4,
        'GROW_SEARCH_INTENT',
        `Exploit search demand: ${gsc.top_opportunity.top_query ?? site.name}`,
        `${gsc.opportunity_impressions} impressions and ${gsc.opportunity_count} opportunity pages are visible in GSC.`,
        'gsc'
      );
      continue;
    }
    if ((ph?.users ?? 0) >= 20) {
      pushAction(
        site,
        5,
        'IMPROVE_CONVERSION',
        'Recent users exist; add or review primary decision path.',
        `${ph.users} PostHog users and ${ph.pageviews} pageviews were seen in the latest 7d probe.`,
        'posthog'
      );
      continue;
    }
    pushAction(
      site,
      6,
      'DISTRIBUTION_TEST',
      'No urgent data issue; run the next distribution test.',
      'The site is visible but lacks a stronger traffic or search opportunity signal in current sources.',
      'owner_score'
    );
  }

  return actions
    .sort((a, b) => a.priority - b.priority || asNumber(b.impact) - asNumber(a.impact) || a.site_name.localeCompare(b.site_name))
    .slice(0, 20);
}

function buildCoverage(siteRows) {
  return {
    generated_at: kstNow(),
    registry_version: REGISTRY_VERSION,
    rows: siteRows.map((row) => ({
      site_id: row.id,
      site_name: row.name,
      status: row.status,
      canonical_host: row.canonical_host,
      ...row.measurement,
    })),
  };
}

function buildPerformanceSummary(siteRows, dataTrustState) {
  const active = siteRows.filter((row) => row.status === 'active_live');
  const totals = active.reduce(
    (acc, site) => {
      const p = site.performance ?? {};
      acc.today_visitors += asNumber(p.today_visitors);
      acc.yesterday_visitors += asNumber(p.yesterday_visitors);
      acc.visitors_7d += asNumber(p.visitors_7d);
      acc.pageviews_7d += asNumber(p.pageviews_7d);
      acc.decision_events_7d += asNumber(p.decision_events_7d);
      if (p.visitors_prev_7d !== null && p.visitors_prev_7d !== undefined) {
        acc.visitors_7d_comparable += asNumber(p.visitors_7d);
        acc.visitors_prev_7d += asNumber(p.visitors_prev_7d);
      }
      if (p.pageviews_prev_7d !== null && p.pageviews_prev_7d !== undefined) {
        acc.pageviews_7d_comparable += asNumber(p.pageviews_7d);
        acc.pageviews_prev_7d += asNumber(p.pageviews_prev_7d);
      }
      if (p.decision_events_prev_7d !== null && p.decision_events_prev_7d !== undefined) {
        acc.decision_events_7d_comparable += asNumber(p.decision_events_7d);
        acc.decision_events_prev_7d += asNumber(p.decision_events_prev_7d);
      }
      return acc;
    },
    {
      today_visitors: 0,
      yesterday_visitors: 0,
      visitors_7d: 0,
      visitors_prev_7d: 0,
      visitors_7d_comparable: 0,
      pageviews_7d: 0,
      pageviews_prev_7d: 0,
      pageviews_7d_comparable: 0,
      decision_events_7d: 0,
      decision_events_prev_7d: 0,
      decision_events_7d_comparable: 0,
    }
  );

  const topByVisitors = active
    .slice()
    .sort((a, b) => asNumber(b.performance?.visitors_7d) - asNumber(a.performance?.visitors_7d))[0] ?? null;
  const topGrowth = active
    .filter((site) => site.performance?.visitors_delta_pct !== null && site.performance?.visitors_delta_pct !== undefined)
    .sort((a, b) => asNumber(b.performance?.visitors_delta_pct) - asNumber(a.performance?.visitors_delta_pct))[0] ?? null;
  const topDrop = active
    .filter((site) => site.performance?.visitors_delta_pct !== null && site.performance?.visitors_delta_pct !== undefined)
    .sort((a, b) => asNumber(a.performance?.visitors_delta_pct) - asNumber(b.performance?.visitors_delta_pct))[0] ?? null;
  const topConversionLeak = active
    .filter((site) => site.performance?.stage === 'conversion_leak' || site.performance?.signals?.includes('conversion_leak'))
    .sort((a, b) => asNumber(b.performance?.visitors_7d) - asNumber(a.performance?.visitors_7d))[0] ?? null;
  const primarySource = active.some((site) => site.performance?.primary_source === 'posthog') ? 'posthog' : 'ga4';
  const decisionRate = rate(totals.decision_events_7d, totals.pageviews_7d);
  const visitorsDelta = totals.visitors_prev_7d > 0 ? deltaPct(totals.visitors_7d_comparable, totals.visitors_prev_7d) : null;
  const pageviewsDelta = totals.pageviews_prev_7d > 0 ? deltaPct(totals.pageviews_7d_comparable, totals.pageviews_prev_7d) : null;
  const decisionDelta = totals.decision_events_prev_7d > 0 ? deltaPct(totals.decision_events_7d_comparable, totals.decision_events_prev_7d) : null;
  const headline =
    totals.visitors_7d > 0
      ? `최근 7일 방문자는 ${totals.visitors_7d.toLocaleString('ko-KR')}명, 성과 이벤트는 ${totals.decision_events_7d.toLocaleString('ko-KR')}건입니다.`
      : '최근 7일 방문자 신호가 약합니다.';

  return {
    primary_source: primarySource,
    trust_state: dataTrustState,
    today_visitors: totals.today_visitors,
    yesterday_visitors: totals.yesterday_visitors,
    visitors_7d: totals.visitors_7d,
    visitors_prev_7d: totals.visitors_prev_7d > 0 ? totals.visitors_prev_7d : null,
    visitors_7d_delta_pct: visitorsDelta,
    pageviews_7d: totals.pageviews_7d,
    pageviews_prev_7d: totals.pageviews_prev_7d > 0 ? totals.pageviews_prev_7d : null,
    pageviews_7d_delta_pct: pageviewsDelta,
    decision_events_7d: totals.decision_events_7d,
    decision_events_prev_7d: totals.decision_events_prev_7d > 0 ? totals.decision_events_prev_7d : null,
    decision_events_delta_pct: decisionDelta,
    decision_rate_7d: decisionRate,
    top_site_by_visitors: topByVisitors?.id ?? null,
    top_site_by_visitors_name: topByVisitors?.name ?? null,
    top_site_by_growth: topGrowth?.id ?? null,
    top_site_by_drop: topDrop?.id ?? null,
    top_conversion_leak: topConversionLeak?.id ?? null,
    top_conversion_leak_name: topConversionLeak?.name ?? null,
    headline,
  };
}

function buildSnapshot() {
  const sources = buildSources();
  const previous = safeReadJson(SNAPSHOT_PATH);
  const generatedAt = kstNow();
  const rawRows = REGISTRY.map((site) => buildSiteRow(site, sources));
  const initialFindings = buildFindings(rawRows);
  const siteRows = applyMeasurementBlocks(rawRows, initialFindings);
  const findings = buildFindings(siteRows);
  const actions = buildActions(siteRows, findings);
  const maxStale = Math.max(
    0,
    ...sources.sourceRuns
      .map((source) => source.stale_seconds)
      .filter((value) => Number.isFinite(value))
  );
  const hasP0 = findings.some((entry) => entry.severity === 'P0');
  const hasP1OrP2 = findings.some((entry) => ['P1', 'P2'].includes(entry.severity));
  const dataTrustState = hasP0 ? 'blocked' : hasP1OrP2 ? 'degraded' : 'trusted';
  const performanceSummary = buildPerformanceSummary(siteRows, dataTrustState);

  return {
    snapshot_version: SNAPSHOT_VERSION,
    snapshot_id: stableId('ots', generatedAt),
    generated_at: generatedAt,
    timezone: TIMEZONE,
    source_runs: sources.sourceRuns,
    source_errors: sources.sourceErrors,
    stale_seconds: maxStale,
    data_trust_state: dataTrustState,
    is_last_good: false,
    supersedes_snapshot_id: previous.json?.snapshot_id ?? null,
    registry_version: REGISTRY_VERSION,
    redaction: {
      applied: true,
      rules: [
        'no raw secrets',
        'no credential file paths',
        'no raw GA property numeric ids in owner snapshot',
        'API error bodies are summarized only',
      ],
    },
    performance_summary: performanceSummary,
    summary: {
      active_sites: siteRows.filter((row) => row.status === 'active_live').length,
      candidate_sites: siteRows.filter((row) => row.status === 'candidate_decision').length,
      blocked_by_measurement: siteRows.filter((row) => row.blocked_by_measurement).length,
      top_actions: actions.slice(0, 3).map((action) => action.id),
      findings_by_severity: ['P0', 'P1', 'P2', 'P3'].reduce((acc, severity) => {
        acc[severity] = findings.filter((entry) => entry.severity === severity).length;
        return acc;
      }, {}),
    },
    sites: siteRows,
    findings,
    actions,
  };
}

function validateSnapshot(snapshot) {
  const errors = [];
  for (const key of ['snapshot_version', 'snapshot_id', 'generated_at', 'timezone', 'source_runs', 'source_errors', 'stale_seconds', 'data_trust_state', 'is_last_good', 'registry_version', 'performance_summary', 'sites', 'findings', 'actions']) {
    if (!(key in snapshot)) errors.push(`missing snapshot key: ${key}`);
  }
  const activeIds = REGISTRY.filter((site) => site.status === 'active_live').map((site) => site.id);
  const snapshotIds = new Set((snapshot.sites ?? []).map((site) => site.id));
  for (const siteId of activeIds) {
    if (!snapshotIds.has(siteId)) errors.push(`active site missing from snapshot: ${siteId}`);
  }
  if (!Array.isArray(snapshot.actions) || snapshot.actions.length === 0) errors.push('actions must not be empty');
  if (!Number.isFinite(Number(snapshot.performance_summary?.visitors_7d))) errors.push('performance_summary.visitors_7d must be numeric');
  if (!Number.isFinite(Number(snapshot.performance_summary?.pageviews_7d))) errors.push('performance_summary.pageviews_7d must be numeric');
  if (!Number.isFinite(Number(snapshot.performance_summary?.decision_events_7d))) errors.push('performance_summary.decision_events_7d must be numeric');
  return errors;
}

function main() {
  const snapshot = buildSnapshot();
  const validationErrors = validateSnapshot(snapshot);
  if (validationErrors.length) {
    const previous = safeReadJson(SNAPSHOT_PATH);
    if (previous.ok && previous.json) {
      const fallback = {
        ...previous.json,
        is_last_good: true,
        source_errors: [
          ...(previous.json.source_errors ?? []),
          { source: 'owner_traffic_command', error: validationErrors.join('; ') },
        ],
      };
      atomicWriteJson(SNAPSHOT_PATH, fallback);
      console.log(JSON.stringify({ ok: false, used_last_good: true, errors: validationErrors }, null, 2));
      process.exitCode = 1;
      return;
    }
    console.error(JSON.stringify({ ok: false, errors: validationErrors }, null, 2));
    process.exit(1);
  }

  atomicWriteJson(ALLOWLIST_PATH, DECISION_EVENT_ALLOWLIST);
  atomicWriteJson(REGISTRY_PATH, { version: REGISTRY_VERSION, generated_at: snapshot.generated_at, sites: REGISTRY });
  atomicWriteJson(COVERAGE_PATH, buildCoverage(snapshot.sites));
  atomicWriteJson(SNAPSHOT_PATH, snapshot);
  console.log(
    JSON.stringify(
      {
        ok: true,
        snapshot: rel(SNAPSHOT_PATH),
        registry: rel(REGISTRY_PATH),
        coverage: rel(COVERAGE_PATH),
        sites: snapshot.sites.length,
        data_trust_state: snapshot.data_trust_state,
        top_actions: snapshot.actions.slice(0, 3).map((action) => `${action.site_id}:${action.action_class}`),
      },
      null,
      2
    )
  );
}

main();
