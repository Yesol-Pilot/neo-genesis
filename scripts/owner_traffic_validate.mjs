#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const ROOT = path.resolve(__dirname, '..');
const OUT_DIR = path.join(ROOT, 'data', 'owner-analytics');

const REQUIRED_SNAPSHOT_KEYS = [
  'snapshot_version',
  'snapshot_id',
  'generated_at',
  'timezone',
  'source_runs',
  'source_errors',
  'stale_seconds',
  'data_trust_state',
  'is_last_good',
  'supersedes_snapshot_id',
  'registry_version',
  'performance_summary',
  'sites',
  'findings',
  'actions',
];

const SECRET_PATTERNS = [
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
  /\bAIza[0-9A-Za-z_-]{20,}\b/,
  /\bgh[pousr]_[0-9A-Za-z_]{20,}\b/,
  /\bsk-[0-9A-Za-z_-]{20,}\b/,
  /\bphx_[0-9A-Za-z_-]{20,}\b/,
  /"private_key"\s*:/,
  /"client_secret"\s*:/,
  /"refresh_token"\s*:/,
  /properties\/\d{4,}/,
];

function readJson(filePath) {
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

function assert(condition, errors, message) {
  if (!condition) errors.push(message);
}

function hasSourceConflict(primaryValue, secondaryValue) {
  const primary = Number(primaryValue);
  const secondary = Number(secondaryValue);
  if (!Number.isFinite(primary) || !Number.isFinite(secondary)) return false;
  if (primary <= 0 || secondary <= 0) return false;
  const high = Math.max(primary, secondary);
  const low = Math.min(primary, secondary);
  return high >= 20 && (high - low) / high >= 0.5;
}

function containsMojibake(value) {
  if (typeof value !== 'string') return false;
  return /\uFFFD/.test(value) || /\?[ㄱ-ㅎㅏ-ㅣ가-힣]/.test(value) || /[ㄱ-ㅎㅏ-ㅣ가-힣]\?/.test(value);
}

function scanText(filePath, patterns) {
  const text = fs.readFileSync(filePath, 'utf8');
  return patterns.filter((pattern) => pattern.test(text)).map((pattern) => String(pattern));
}

function validateSnapshot(errors, warnings) {
  const snapshotPath = path.join(OUT_DIR, 'owner-traffic-latest.json');
  const registryPath = path.join(OUT_DIR, 'site_registry.json');
  const coveragePath = path.join(OUT_DIR, 'source_coverage_matrix.json');
  const allowlistPath = path.join(OUT_DIR, 'decision_event_allowlist.json');

  for (const filePath of [snapshotPath, registryPath, coveragePath, allowlistPath]) {
    assert(fs.existsSync(filePath), errors, `missing file: ${path.relative(ROOT, filePath)}`);
  }
  if (errors.length) return null;

  const snapshot = readJson(snapshotPath);
  const registry = readJson(registryPath);
  const coverage = readJson(coveragePath);
  const allowlist = readJson(allowlistPath);

  for (const key of REQUIRED_SNAPSHOT_KEYS) {
    assert(Object.prototype.hasOwnProperty.call(snapshot, key), errors, `snapshot missing key: ${key}`);
  }

  const activeRegistrySites = (registry.sites ?? []).filter((site) => site.status === 'active_live');
  const snapshotSiteIds = new Set((snapshot.sites ?? []).map((site) => site.id));
  for (const site of activeRegistrySites) {
    assert(snapshotSiteIds.has(site.id), errors, `active site missing from snapshot: ${site.id}`);
  }

  assert((snapshot.sites ?? []).length >= activeRegistrySites.length, errors, 'snapshot site count is smaller than active registry count');
  assert(Array.isArray(snapshot.actions) && snapshot.actions.length > 0, errors, 'snapshot actions must not be empty');
  assert(Array.isArray(snapshot.findings), errors, 'snapshot findings must be an array');
  assert(['trusted', 'degraded', 'blocked'].includes(snapshot.data_trust_state), errors, 'invalid data_trust_state');
  assert(Number.isFinite(Number(snapshot.performance_summary?.visitors_7d)), errors, 'performance_summary.visitors_7d must be numeric');
  assert(Number.isFinite(Number(snapshot.performance_summary?.pageviews_7d)), errors, 'performance_summary.pageviews_7d must be numeric');
  assert(Number.isFinite(Number(snapshot.performance_summary?.decision_events_7d)), errors, 'performance_summary.decision_events_7d must be numeric');
  assert((snapshot.sites ?? []).every((site) => site.performance), errors, 'every site must include performance');
  for (const site of snapshot.sites ?? []) {
    const performance = site.performance ?? {};
    assert(['posthog', 'ga4', 'none'].includes(performance.primary_source), errors, `invalid primary_source: ${site.id}`);
    assert(['trusted', 'degraded', 'blocked'].includes(performance.trust_state), errors, `invalid performance trust_state: ${site.id}`);
    assert(Array.isArray(performance.signals), errors, `performance.signals must be an array: ${site.id}`);
    if (performance.primary_source === 'none') {
      assert(performance.trust_state !== 'trusted', errors, `source-less site must not be trusted: ${site.id}`);
    }
    if (hasSourceConflict(performance.posthog_visitors_7d, performance.ga4_visitors_7d)) {
      assert(performance.source_conflict === true, errors, `source conflict not flagged: ${site.id}`);
      assert(performance.trust_state === 'degraded', errors, `source conflict must degrade trust: ${site.id}`);
    }
  }

  const coverageIds = new Set((coverage.rows ?? []).map((row) => row.site_id));
  for (const site of registry.sites ?? []) {
    assert(coverageIds.has(site.id), errors, `coverage matrix missing site: ${site.id}`);
  }

  const sourceRuns = snapshot.source_runs ?? [];
  for (const source of ['ga4', 'posthog', 'gsc']) {
    assert(sourceRuns.some((run) => run.source === source && run.ok), errors, `source run missing or failed: ${source}`);
  }
  for (const run of sourceRuns.filter((item) => item.ok)) {
    assert(run.generated_at, errors, `source run missing generated_at: ${run.source}:${run.path}`);
  }

  const allowlistEvents = allowlist.numerator_events ?? [];
  assert(Array.isArray(allowlistEvents) && allowlistEvents.length >= 10, errors, 'decision allowlist is too small');
  assert(!allowlistEvents.includes('$pageview'), errors, 'decision allowlist must not include $pageview');

  const actionSiteKeys = new Set();
  for (const action of snapshot.actions.slice(0, 8)) {
    const key = `${action.site_id}:${action.action_class}`;
    assert(!actionSiteKeys.has(key), errors, `duplicate top action for site/class: ${key}`);
    actionSiteKeys.add(key);
  }

  const findingsByCode = new Map();
  for (const finding of snapshot.findings ?? []) {
    findingsByCode.set(finding.code, (findingsByCode.get(finding.code) ?? 0) + 1);
  }
  assert(!findingsByCode.has('POSTHOG_DECISION_EVENT_UNAVAILABLE'), errors, 'PostHog latest output still lacks decision events');
  assert(findingsByCode.has('POSTHOG_DECISION_EVENT_ZERO'), warnings, 'No decision-event-zero finding is present; verify fixtures still cover it');
  assert(
    findingsByCode.has('GA4_TAG_MISSING') ||
      findingsByCode.has('GA4_COLLECTION_LAG_OR_BLOCKED') ||
      findingsByCode.has('GA4_WINDOW_MISMATCH'),
    warnings,
    'No GA4 tracking integrity finding is present; live issue may be resolved'
  );

  const snapshotSecretHits = scanText(snapshotPath, SECRET_PATTERNS);
  assert(snapshotSecretHits.length === 0, errors, `owner snapshot contains redaction hit: ${snapshotSecretHits.join(', ')}`);

  return { snapshot, registry, coverage, allowlist };
}

function validateSourceCode(errors) {
  const posthogPath = path.join(ROOT, 'scripts', 'posthog_traffic.py');
  const ownerPath = path.join(ROOT, 'scripts', 'owner_traffic_command.mjs');
  const posthogText = fs.readFileSync(posthogPath, 'utf8');
  const ownerText = fs.readFileSync(ownerPath, 'utf8');
  assert(/decisionEvents/.test(posthogText), errors, 'posthog_traffic.py must emit decisionEvents');
  assert(/legacyActionEvents/.test(posthogText), errors, 'posthog_traffic.py must emit legacyActionEvents separately');
  assert(!/countIf\(event != '\$pageview'\)\s+AS\s+action_events/i.test(posthogText), errors, 'PostHog broad non-pageview count is still named action_events');
  assert(!/POSTHOG_DECISION_EVENT_UNAVAILABLE/.test(ownerText) || /decision_events === null/.test(ownerText), errors, 'owner normalizer must only emit decision-unavailable when field is null');
  assert(/hasSourceConflict/.test(ownerText), errors, 'owner performance must flag GA4/PostHog source conflicts');
  assert(/primarySource === 'none'/.test(ownerText), errors, 'owner performance must degrade trust when no traffic source exists');
  assert(/signals\.includes\('traffic_drop'\)/.test(ownerText) && /signals\.includes\('conversion_leak'\)/.test(ownerText), errors, 'traffic drop and conversion leak signals must both be modeled');
}

function validateFixtures(errors) {
  const fixtureDir = path.join(OUT_DIR, 'fixtures');
  const mojibakePath = path.join(fixtureDir, 'korean-mojibake.json');
  const decisionZeroPath = path.join(fixtureDir, 'posthog-decision-zero.json');
  const lastGoodPath = path.join(fixtureDir, 'last-good-fallback.json');

  for (const filePath of [mojibakePath, decisionZeroPath, lastGoodPath]) {
    assert(fs.existsSync(filePath), errors, `missing fixture: ${path.relative(ROOT, filePath)}`);
  }
  if (errors.length) return;

  const mojibake = readJson(mojibakePath);
  assert(containsMojibake(mojibake.sample), errors, 'korean mojibake fixture is not detected');

  const decisionZero = readJson(decisionZeroPath);
  assert(decisionZero.posthog.pageviews >= 20 && decisionZero.posthog.decisionEvents === 0, errors, 'decision-zero fixture does not trigger the threshold');

  const lastGood = readJson(lastGoodPath);
  assert(lastGood.is_last_good === true && lastGood.source_errors.length > 0, errors, 'last-good fixture must show fallback semantics');
}

function main() {
  const errors = [];
  const warnings = [];
  const context = validateSnapshot(errors, warnings);
  validateSourceCode(errors);
  validateFixtures(errors);

  const report = {
    ok: errors.length === 0,
    errors,
    warnings,
    snapshot_id: context?.snapshot?.snapshot_id ?? null,
    data_trust_state: context?.snapshot?.data_trust_state ?? null,
    active_sites: (context?.registry?.sites ?? []).filter((site) => site.status === 'active_live').length,
    snapshot_sites: context?.snapshot?.sites?.length ?? null,
    top_actions: (context?.snapshot?.actions ?? []).slice(0, 3).map((action) => `${action.site_id}:${action.action_class}`),
  };
  console.log(JSON.stringify(report, null, 2));
  if (errors.length) process.exit(1);
}

main();
