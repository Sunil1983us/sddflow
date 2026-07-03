#!/usr/bin/env node
// Copies the 5 sdd-* pack folders into cli/packs/ so `sdd init` can find
// them once this package is installed from npm (a published tarball
// contains only what "files" in package.json lists — the rest of the
// monorepo, including packs/, is not there unless bundled here first).
//
// Runs automatically via the "prepublishOnly" npm lifecycle hook — `npm
// publish` cannot skip it, unlike a manually-remembered build step. This
// mirrors cli-python/publish.sh, which does the same job for the Python
// package (copies packs/ into cli-python/sdd/packs/ before building).
//
// cli/packs/ is a generated build artifact — never commit it; it's
// regenerated here every time and .gitignored.

import { existsSync, mkdirSync, rmSync, cpSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const cliRoot   = resolve(__dirname, '..');
const repoRoot  = resolve(cliRoot, '..');
const packsSrc  = resolve(repoRoot, 'packs');
const packsDest = resolve(cliRoot, 'packs');

const PACKS = [
  'sdd-backend-service',
  'sdd-frontend-spa',
  'sdd-fullstack',
  'sdd-mobile',
  'sdd-universal',
];

rmSync(packsDest, { recursive: true, force: true });
mkdirSync(packsDest, { recursive: true });

for (const pack of PACKS) {
  const src = resolve(packsSrc, pack);
  if (!existsSync(src)) {
    console.error(`✗  ${pack} not found at ${src} — aborting`);
    process.exit(1);
  }
  cpSync(src, resolve(packsDest, pack), { recursive: true });
  console.log(`✓  bundled ${pack}`);
}

console.log(`\nBundled ${PACKS.length} packs into ${packsDest}`);
