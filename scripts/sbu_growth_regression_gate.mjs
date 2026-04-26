#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const DEFAULT_REPORT = path.join(ROOT, 'data', 'sbu-growth', 'control-tower-latest.json');

function parseArgs(argv) {
  const args = { report: DEFAULT_REPORT, json: false };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--report') args.report = path.resolve(argv[++i] || DEFAULT_REPORT);
    else if (arg === '--json') args.json = true;
  }
  return args;
}

function addIssue(issues, site, code, message) {
  issues.push({ site: site.id, code, message });
}

function checkSite(site) {
  const issues = [];
  const warnings = [];
  const posts = site.local?.posts || {};
  const git = site.local?.git || {};
  const vercel = site.local?.vercel || {};
  const live = site.live || {};

  if (!posts.fresh) addIssue(issues, site, 'stale_content', 'Latest post is outside the freshness gate.');
  if ((posts.mauGap || 0) > 0) addIssue(issues, site, 'mau_gap', `Modeled MAU gap remains: ${posts.mauGap}.`);
  if (!posts.latest?.slug) addIssue(issues, site, 'missing_latest_post', 'No latest MDX post detected.');
  if (!vercel.hasProject) addIssue(issues, site, 'missing_vercel_project', 'Vercel project metadata is missing.');
  if (!git.remoteOk) addIssue(issues, site, 'git_remote_mismatch', 'Git remote does not match expected Yesol-Pilot repository.');
  if (!git.emailOk) addIssue(issues, site, 'git_email_mismatch', 'Git user.email is not dpthf1537@gmail.com.');
  if (git.dirty) warnings.push({ site: site.id, code: 'dirty_worktree', message: 'SBU working tree has uncommitted changes; skip automated deploy until reviewed.' });

  if (!site.live) {
    addIssue(issues, site, 'live_not_checked', 'Live verification was not run.');
  } else {
    if (!live.blog?.ok) addIssue(issues, site, 'live_blog_failed', 'Live /blog does not expose the latest post.');
    if (!live.detail?.ok) addIssue(issues, site, 'live_detail_failed', 'Live latest detail page failed verification.');
    if (!live.sitemap?.ok) addIssue(issues, site, 'sitemap_failed', 'Live sitemap does not include the latest post.');
    if (!live.robots?.ok) addIssue(issues, site, 'robots_failed', 'robots.txt did not return 200.');
  }

  if ((posts.ctaCoverage || 0) < 0.7) warnings.push({ site: site.id, code: 'cta_coverage_low', message: `CTA coverage ${posts.ctaCoverage}.` });
  if ((posts.internalLinkCoverage || 0) < 0.6) warnings.push({ site: site.id, code: 'internal_link_coverage_low', message: `Internal link coverage ${posts.internalLinkCoverage}.` });

  return { issues, warnings };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const report = JSON.parse(fs.readFileSync(args.report, 'utf8'));
  const issues = [];
  const warnings = [];

  for (const site of report.sites || []) {
    const result = checkSite(site);
    issues.push(...result.issues);
    warnings.push(...result.warnings);
  }

  const output = {
    report: path.relative(ROOT, args.report),
    generatedAt: report.generatedAt,
    passed: issues.length === 0,
    criticalIssueCount: issues.length,
    warningCount: warnings.length,
    issues,
    warnings,
  };

  if (args.json) {
    console.log(JSON.stringify(output, null, 2));
  } else {
    console.log(`# SBU Growth Regression Gate\n`);
    console.log(`- report: ${output.report}`);
    console.log(`- generatedAt: ${output.generatedAt}`);
    console.log(`- passed: ${output.passed}`);
    console.log(`- criticalIssues: ${output.criticalIssueCount}`);
    console.log(`- warnings: ${output.warningCount}`);
    if (issues.length) {
      console.log('\n## Critical Issues');
      for (const issue of issues) console.log(`- ${issue.site} / ${issue.code}: ${issue.message}`);
    }
    if (warnings.length) {
      console.log('\n## Improvement Warnings');
      for (const warning of warnings) console.log(`- ${warning.site} / ${warning.code}: ${warning.message}`);
    }
  }

  if (issues.length > 0) process.exit(1);
}

main();
