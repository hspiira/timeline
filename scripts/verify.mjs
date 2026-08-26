#!/usr/bin/env node
/**
 * The single verify command. CI runs this and nothing else; run it locally to
 * get the same answer before pushing.
 *
 * Build is absolute. Types and lint are ratcheted against ci/*-baseline.txt: a
 * count above the baseline fails, a count below it reports the new number to
 * record. On GitHub Actions the same messages come out as ::error:: and
 * ::notice:: annotations.
 */

import { spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const onActions = process.env.GITHUB_ACTIONS === 'true';

const run = (args, { capture = false } = {}) =>
  spawnSync('pnpm', args, {
    cwd: root,
    encoding: 'utf8',
    stdio: capture ? ['ignore', 'pipe', 'pipe'] : 'inherit',
    shell: process.platform === 'win32',
  });

const baseline = (file) => Number(readFileSync(join(root, 'ci', file), 'utf8').trim());
const notice = (message) => console.log(onActions ? `::notice::${message}` : message);
const group = (title) => console.log(onActions ? `::group::${title}` : `\n> ${title}`);
const endGroup = () => onActions && console.log('::endgroup::');

const failures = [];

// Build: a failure here means the app does not run at all.
group('build');
if (run(['build']).status !== 0) {
  failures.push('Build failed.');
}
endGroup();

// Types.
group('types');
const tsc = run(['exec', 'tsc', '--noEmit', '-p', 'tsconfig.json'], { capture: true });
const tscOutput = `${tsc.stdout}${tsc.stderr}`;
const tscCount = tscOutput.split('\n').filter((line) => line.includes('error TS')).length;
const tscBaseline = baseline('tsc-baseline.txt');
console.log(`type errors: ${tscCount} (baseline ${tscBaseline})`);
if (tscCount > tscBaseline) {
  process.stdout.write(tscOutput);
}
endGroup();
if (tscCount > tscBaseline) {
  failures.push(`Type errors rose from ${tscBaseline} to ${tscCount}.`);
} else if (tscCount < tscBaseline) {
  notice(`Type errors down to ${tscCount}. Update ci/tsc-baseline.txt to lock it in.`);
}

// Lint.
group('lint');
const biome = run(['exec', 'biome', 'check', 'src'], { capture: true });
const biomeOutput = `${biome.stdout}${biome.stderr}`;
const biomeCount = [...biomeOutput.matchAll(/Found (\d+) (?:warnings|errors)/g)].reduce(
  (total, match) => total + Number(match[1]),
  0,
);
const biomeBaseline = baseline('biome-baseline.txt');
console.log(`biome findings: ${biomeCount} (baseline ${biomeBaseline})`);
if (biomeCount > biomeBaseline) {
  process.stdout.write(biomeOutput);
}
endGroup();
if (biomeCount > biomeBaseline) {
  failures.push(`Lint findings rose from ${biomeBaseline} to ${biomeCount}.`);
} else if (biomeCount < biomeBaseline) {
  notice(`Lint findings down to ${biomeCount}. Update ci/biome-baseline.txt to lock it in.`);
}

console.log('');
if (failures.length > 0) {
  for (const failure of failures) console.error(onActions ? `::error::${failure}` : `FAIL: ${failure}`);
  process.exit(1);
}
console.log('verify passed');
