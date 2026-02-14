#!/usr/bin/env node
/**
 * Generate TypeScript types from the OpenAPI spec.
 * Requires a running server that serves /openapi.json.
 *
 * Uses OPENAPI_URL or API_URL (default: http://localhost:8000).
 */

import { execSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const baseUrl = process.env.OPENAPI_URL || process.env.API_URL || 'http://localhost:8000';
const specUrl = `${baseUrl.replace(/\/$/, '')}/openapi.json`;
const outFile = join(dirname(fileURLToPath(import.meta.url)), '..', 'src', 'lib', 'timeline-api.ts');

execSync(`npx openapi-typescript "${specUrl}" -o "${outFile}"`, {
  stdio: 'inherit',
});
