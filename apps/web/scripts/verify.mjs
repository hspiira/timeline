#!/usr/bin/env node
/**
 * The single verify command. CI runs this and nothing else.
 *
 * Build and tests must pass. Types, lint and style are ratcheted against
 * ci/*-baseline.txt: a count above the baseline fails, a count below it prints the
 * number to record.
 *
 * End-to-end tests need the app and the API running, so they are opt-in: set
 * VERIFY_E2E=1. Without it they are reported as not run, never as passed.
 */

import { spawn, spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const onActions = process.env.GITHUB_ACTIONS === 'true';

const colour = (code, text) => (onActions ? text : `\u001b[${code}m${text}\u001b[0m`);
const green = (text) => colour('32', text);
const red = (text) => colour('31', text);
const yellow = (text) => colour('33', text);
const bold = (text) => colour('1', text);

const notice = (message) => console.log(onActions ? `::notice::${message}` : yellow(message));
const group = (title) => console.log(onActions ? `::group::${title}` : `\n${bold(`> ${title}`)}`);
const endGroup = () => onActions && console.log('::endgroup::');

const fatal = (message) => {
  console.error(onActions ? `::error::${message}` : red(`FAIL: ${message}`));
  process.exit(1);
};

const plain = (text) => text.replace(/\u001b\[[0-9;]*m/g, '');

const run = (args) => {
  const label = `pnpm ${args.join(' ')}`;
  const result = spawnSync('pnpm', args, {
    cwd: root,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'pipe'],
    shell: process.platform === 'win32',
    // Output is piped so findings can be counted, and every one of these tools
    // drops colour when it is not writing to a terminal.
    env: { ...process.env, FORCE_COLOR: '1' },
    maxBuffer: 64 * 1024 * 1024,
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

const tally = (values) => {
  const counts = new Map();
  for (const value of values) counts.set(value, (counts.get(value) ?? 0) + 1);
  return [...counts].sort((a, b) => b[1] - a[1]);
};

const breakdown = (rows, { top = 6, total, label } = {}) => {
  if (rows.length === 0) return;
  if (label) console.log(`  ${label}`);
  const attributed = rows.reduce((sum, [, count]) => sum + count, 0);
  if (total !== undefined && attributed < total) {
    rows = [...rows, ['unattributed', total - attributed]];
  }
  const shown = rows.slice(0, top);
  const width = Math.max(...shown.map(([label]) => label.length));
  for (const [label, count] of shown) {
    console.log(`    ${label.padEnd(width)}  ${String(count).padStart(4)}`);
  }
  const rest = rows.slice(top);
  if (rest.length > 0) {
    const total = rest.reduce((sum, [, count]) => sum + count, 0);
    console.log(`    ${`+ ${rest.length} more`.padEnd(width)}  ${String(total).padStart(4)}`);
  }
};

const ratchet = ({ name, count, baselineFile, brokenCheck, output, detail = [], detailLabel }) => {
  if (brokenCheck) {
    process.stdout.write(output);
    failures.push(`${name} check is broken: the tool failed but reported no findings.`);
    return;
  }
  const recorded = baseline(baselineFile);
  const tint = count > recorded ? red : count < recorded ? yellow : green;
  console.log(`${name}: ${tint(String(count))} (baseline ${recorded})`);
  breakdown(detail, { total: count, label: detailLabel });
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
    const child = spawn('pnpm', ['build'], {
      cwd: root,
      shell: process.platform === 'win32',
      env: { ...process.env, FORCE_COLOR: '1' },
    });
    let hidden = 0;
    let lastWasBlank = false;
    const emit = (line) => {
      const bare = plain(line).trimEnd();
      if (buildNoise.some((pattern) => pattern.test(bare))) {
        hidden += 1;
        return;
      }
      if (bare === '') {
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
  console.log(`${green('build ok')} in ${elapsed}s (${build.hidden} noise lines hidden; run \`pnpm build\` for all of it)`);
} else {
  failures.push('Build failed.');
}
endGroup();

group('types  ·  tsc --noEmit');
const tsc = run(['exec', 'tsc', '--noEmit', '-p', 'tsconfig.json']);
const tscLines = plain(tsc.output).split('\n').filter((line) => line.includes('error TS'));
ratchet({
  name: 'type errors',
  count: tscLines.length,
  baselineFile: 'tsc-baseline.txt',
  brokenCheck: tsc.status !== 0 && tscLines.length === 0,
  output: tsc.output,
  detail: tally(tscLines.map((line) => line.match(/error (TS\d+)/)?.[1] ?? 'other')),
  detailLabel: 'by code',
});
breakdown(tally(tscLines.map((line) => line.match(/^(\S+?)\(/)?.[1] ?? 'other')), {
  top: 4,
  label: 'by file',
});
endGroup();

const countFindings = (output) =>
  [...plain(output).matchAll(/Found (\d+) (?:warnings?|errors?)/g)].reduce(
    (total, match) => total + Number(match[1]),
    0,
  );

group('lint  ·  biome lint src');
const lint = run(['exec', 'biome', 'lint', '--max-diagnostics=1000', 'src']);
const lintCount = countFindings(lint.output);
ratchet({
  name: 'lint findings',
  count: lintCount,
  baselineFile: 'biome-lint-baseline.txt',
  brokenCheck: lint.status !== 0 && lintCount === 0,
  output: lint.output,
  detail: tally(
    [...plain(lint.output).matchAll(/lint\/([a-zA-Z0-9]+\/[a-zA-Z0-9]+)/g)].map((match) => match[1]),
  ),
  detailLabel: 'by rule',
});
endGroup();

group('style  ·  biome check --linter-enabled=false src');
const style = run(['exec', 'biome', 'check', '--linter-enabled=false', '--max-diagnostics=1000', 'src']);
const styleCount = countFindings(style.output);
ratchet({
  name: 'style findings',
  count: styleCount,
  baselineFile: 'biome-style-baseline.txt',
  brokenCheck: style.status !== 0 && styleCount === 0,
  output: style.output,
  detail: (() => {
    const imports = [...plain(style.output).matchAll(/organizeImports/g)].length;
    return [
      ['formatting', styleCount - imports],
      ['import order', imports],
    ].filter(([, count]) => count > 0);
  })(),
});
endGroup();

group('tests');
const unit = run(['test']);
if (unit.status === 0) {
  console.log(green('tests ok'));
} else {
  process.stdout.write(unit.output);
  failures.push('Tests failed.');
}
endGroup();

group('end-to-end');
if (process.env.VERIFY_E2E === '1') {
  const e2e = run(['test:e2e']);
  if (e2e.status === 0) {
    console.log(green('end-to-end ok'));
  } else {
    process.stdout.write(e2e.output);
    failures.push('End-to-end tests failed.');
  }
} else {
  console.log(yellow('end-to-end not run (needs the app and API up; set VERIFY_E2E=1)'));
}
endGroup();

console.log('');
if (failures.length > 0) {
  // No baseline advice on a failed run: a file that will not parse makes tsc
  // bail early, and the low count it reports is not progress.
  for (const failure of failures) console.error(onActions ? `::error::${failure}` : red(`FAIL: ${failure}`));
  process.exit(1);
}
for (const win of wins) notice(win);
console.log(green('verify passed'));
