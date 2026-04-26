#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const NODE = process.execPath;
const PYTHON = process.platform === 'win32' ? 'python' : 'python3';
const OUTPUT_DIR = path.join(ROOT, 'data', 'sbu-growth');

function parseArgs(argv) {
  const args = {
    withAnalytics: false,
    skipPublisherVerify: false,
  };
  for (const arg of argv) {
    if (arg === '--with-analytics') args.withAnalytics = true;
    else if (arg === '--skip-publisher-verify') args.skipPublisherVerify = true;
  }
  return args;
}

function kstStamp() {
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

function runStep(name, cmd, args, options = {}) {
  const startedAt = kstStamp();
  const result = spawnSync(cmd, args, {
    cwd: ROOT,
    encoding: 'utf8',
    shell: false,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
  const endedAt = kstStamp();
  const stdout = (result.stdout || '').trim();
  const stderr = (result.stderr || '').trim();
  const ok = result.status === 0 || Boolean(options.allowFailure);
  return {
    name,
    cmd: [cmd, ...args].join(' '),
    status: result.status,
    ok: result.status === 0,
    allowedFailure: Boolean(options.allowFailure),
    startedAt,
    endedAt,
    stdoutTail: stdout.split(/\r?\n/).slice(-60).join('\n'),
    stderrTail: stderr.split(/\r?\n/).slice(-40).join('\n'),
    gateOk: ok,
  };
}

function makeMarkdown(report) {
  const lines = [
    '# SBU Growth Loop',
    '',
    `- generatedAt: ${report.generatedAt}`,
    `- passed: ${report.passed}`,
    '',
    '## Steps',
    '',
    '| Step | OK | Status |',
    '|---|---:|---:|',
  ];

  for (const step of report.steps) {
    lines.push(`| ${step.name} | ${step.ok} | ${step.status} |`);
  }

  lines.push('', '## Tails', '');
  for (const step of report.steps) {
    lines.push(`### ${step.name}`, '');
    if (step.stdoutTail) {
      lines.push('```text', step.stdoutTail, '```', '');
    }
    if (step.stderrTail) {
      lines.push('stderr:', '```text', step.stderrTail, '```', '');
    }
  }

  return `${lines.join('\n')}\n`;
}

function writeReport(report) {
  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  const safeStamp = report.generatedAt.replace(/[:+]/g, '-');
  const json = JSON.stringify(report, null, 2);
  const markdown = makeMarkdown(report);
  fs.writeFileSync(path.join(OUTPUT_DIR, 'growth-loop-latest.json'), `${json}\n`, 'utf8');
  fs.writeFileSync(path.join(OUTPUT_DIR, 'growth-loop-latest.md'), markdown, 'utf8');
  fs.writeFileSync(path.join(OUTPUT_DIR, `growth-loop-${safeStamp}.json`), `${json}\n`, 'utf8');
  fs.writeFileSync(path.join(OUTPUT_DIR, `growth-loop-${safeStamp}.md`), markdown, 'utf8');
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const steps = [];

  if (!args.skipPublisherVerify) {
    steps.push(runStep('publisher-verify', NODE, ['scripts/sbu_autonomous_growth_runner.mjs', '--verify-only']));
  }
  steps.push(runStep('control-tower', NODE, ['scripts/sbu_growth_control_tower.mjs', '--json']));
  steps.push(runStep('regression-gate', NODE, ['scripts/sbu_growth_regression_gate.mjs', '--json']));

  if (args.withAnalytics) {
    steps.push(runStep('posthog-7d', PYTHON, ['scripts/posthog_traffic.py', '--days', '7'], { allowFailure: true }));
    steps.push(runStep('ga4-report', PYTHON, ['scripts/ga4_traffic_report.py'], { allowFailure: true }));
  }

  const report = {
    generatedAt: kstStamp(),
    passed: steps.every((step) => step.gateOk),
    steps,
  };
  writeReport(report);
  console.log(makeMarkdown(report));
  if (!report.passed) process.exit(1);
}

main();
