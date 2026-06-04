#!/usr/bin/env node
import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const ROOT = path.resolve(path.dirname(__filename), '..');

function parseArgs(argv) {
  const flags = new Set(argv);
  return {
    skipGa4: flags.has('--skip-ga4'),
    skipPosthog: flags.has('--skip-posthog'),
    fetchGsc: flags.has('--gsc-fetch'),
    skipValidate: flags.has('--skip-validate'),
  };
}

function runStep(name, command, args) {
  return new Promise((resolve, reject) => {
    const started = Date.now();
    console.log(`\n[owner-traffic] ${name}`);
    const child = spawn(command, args, {
      cwd: ROOT,
      shell: process.platform === 'win32',
      stdio: 'inherit',
      env: process.env,
    });
    child.on('error', reject);
    child.on('close', (code) => {
      const seconds = ((Date.now() - started) / 1000).toFixed(1);
      if (code === 0) {
        console.log(`[owner-traffic] ${name} ok (${seconds}s)`);
        resolve();
      } else {
        reject(new Error(`${name} failed with exit code ${code}`));
      }
    });
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const steps = [];
  if (!args.skipGa4) steps.push(['GA4 JSON refresh', 'python', ['scripts/ga4_traffic_json.py']]);
  if (!args.skipPosthog) steps.push(['PostHog decision-event refresh', 'python', ['scripts/posthog_traffic.py', '--days', '7']]);
  if (args.fetchGsc) {
    steps.push([
      'GSC read-only fetch',
      'node',
      ['scripts/sbu_gsc_all.mjs', '--fetch', '--write-default-latest'],
    ]);
  }
  steps.push(['Live tag probe', 'node', ['scripts/owner_traffic_live_probe.mjs']]);
  steps.push(['Owner snapshot normalize', 'node', ['scripts/owner_traffic_command.mjs']]);
  if (!args.skipValidate) steps.push(['Owner snapshot validate', 'node', ['scripts/owner_traffic_validate.mjs']]);

  for (const [name, command, commandArgs] of steps) {
    await runStep(name, command, commandArgs);
  }
  console.log('\n[owner-traffic] complete');
}

main().catch((error) => {
  console.error(`\n[owner-traffic] ${error.message}`);
  process.exit(1);
});
