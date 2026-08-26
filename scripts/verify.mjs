#!/usr/bin/env node
/**
 * The single verify command. CI runs this and nothing else.
 *
 * Build must pass. Types and lint are ratcheted against ci/*-baseline.txt: a
 * count above the baseline fails, a count below it prints the number to record.
 */

import { spawn, spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const onActions = process.env.GITHUB_ACTIONS === 'true';

const notice = (message) => console.log(onActions ? `::notice::${message}` : message);
const group = (title) => console.log(onActions ? `::group::${title}` : `\n> ${title}`);
const endGroup = () => onActions && console.log('::endgroup::');

const fatal = (message) => {
  console.error(onActions ? `::error::${message}` : `FAIL: ${message}`);
  process.exit(1);
};

const run = (args) => {
  const label = `pnpm ${args.join(' ')}`;
  const result = spawnSync('pnpm', args, {
    cwd: root,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: process.platform === 'win32',
  });
  // A null status means the tool never ran or a signal killed it. Counting its
  // empty output would read as "found nothing" and lower the baseline.
  if (result.error) fatal(`Could not run ${label}: ${result.error.message}`);
  if (result.status === null) fatal(`${label} was killed by ${result.signal ?? 'an unknown signal'}.`);
  return { status: result.status, output: `${result.stdout ?? ''}${result.stderr ?? ''}` };
};

const baseline = (file) => {
  let raw;
  try {
    raw = readFileSync(join(root, 'ci', file), 'utf8').trim();
  } catch (error) {
    return fatal(`Could not read ci/${file}: ${error.message}`);
  }
  const value = Number(raw);
  // Every comparison against NaN is false, so a malformed file stops the ratchet.
  if (!Number.isInteger(value) || value < 0) {
    return fatal(`ci/${file} should hold a whole number, but holds ${JSON.stringify(raw)}.`);
  }
  return value;
};

const failures = [];
const wins = [];

const ratchet = ({ name, count, baselineFile, brokenCheck, output }) => {
  if (brokenCheck) {
    process.stdout.write(output);
    failures.push(`${name} check is broken: the tool failed but reported no findings.`);
    return;
  }
  const recorded = baseline(baselineFile);
  console.log(`${name}: ${count} (baseline ${recorded})`);
  if (count > recorded) {
    process.stdout.write(output);
    failures.push(`${name} rose from ${recorded} to ${count}.`);
  } else if (count < recorded) {
    wins.push(`${name} down to ${count}. Update ci/${baselineFile} to lock it in.`);
  }
};

// Vite prints a ~360 line chunk table and one "use client" warning per
// node_modules file. Neither can be turned off in config, and neither can
// carry a build error. Everything else streams through as it happens.
const buildNoise = [
  /^\S+\.[a-z0-9]+\s+[\d.,]+ kB/i,
  /Module level directives cause errors when bundled/,
  /^\(node:\d+\) /,
  /^\(Use `node --trace-deprecation/,
];

const streamBuild = () =>
  new Promise((resolve) => {
    const child = spawn('pnpm', ['build'], { cwd: root, shell: process.platform === 'win32' });
    let hidden = 0;
    let lastWasBlank = false;
    const emit = (line) => {
      const plain = line.replace(/\u001b\[[0-9;]*m/g, '').trimEnd();
      if (buildNoise.some((pattern) => pattern.test(plain))) {
        hidden += 1;
        return;
      }
      if (plain === '') {
        if (lastWasBlank) return;
        lastWasBlank = true;
      } else {
        lastWasBlank = false;
      }
      process.stdout.write(`${line}\n`);
    };

    let pending = '';
    const consume = (chunk) => {
      const lines = (pending + chunk).split('\n');
      pending = lines.pop() ?? '';
      for (const line of lines) emit(line);
    };
    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', consume);
    child.stderr.on('data', consume);
    child.on('error', (error) => fatal(`Could not run pnpm build: ${error.message}`));
    child.on('close', (status, signal) => {
      if (pending) emit(pending);
      if (status === null) fatal(`pnpm build was killed by ${signal ?? 'an unknown signal'}.`);
      resolve({ status, hidden });
    });
  });

group('build');
const startedAt = Date.now();
const build = await streamBuild();
const elapsed = ((Date.now() - startedAt) / 1000).toFixed(1);
if (build.status === 0) {
  console.log(`build ok in ${elapsed}s (${build.hidden} noise lines hidden; run \`pnpm build\` for all of it)`);
} else {
  failures.push('Build failed.');
}
endGroup();

group('types');
const tsc = run(['exec', 'tsc', '--noEmit', '-p', 'tsconfig.json']);
const tscCount = tsc.output.split('\n').filter((line) => line.includes('error TS')).length;
ratchet({
  name: 'type errors',
  count: tscCount,
  baselineFile: 'tsc-baseline.txt',
  brokenCheck: tsc.status !== 0 && tscCount === 0,
  output: tsc.output,
});
endGroup();

group('lint');
const biome = run(['exec', 'biome', 'check', 'src']);
const biomeTotals = [...biome.output.matchAll(/Found (\d+) (?:warnings?|errors?)/g)];
ratchet({
  name: 'biome findings',
  count: biomeTotals.reduce((total, match) => total + Number(match[1]), 0),
  baselineFile: 'biome-baseline.txt',
  brokenCheck: biome.status !== 0 && biomeTotals.length === 0,
  output: biome.output,
});
endGroup();

console.log('');
if (failures.length > 0) {
  // No baseline advice on a failed run: a file that will not parse makes tsc
  // bail early, and the low count it reports is not progress.
  for (const failure of failures) console.error(onActions ? `::error::${failure}` : `FAIL: ${failure}`);
  process.exit(1);
}
for (const win of wins) notice(win);
console.log('verify passed');
