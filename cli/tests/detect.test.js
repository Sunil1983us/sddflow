// Tests for detectProjectType() against ~20 synthetic project fixtures --
// the same set mirrored in cli-python/tests/test_detect.py and
// packs/_shared/tests/test-detect-fixtures.sh, so all three implementations
// are asserted against identical inputs. There was no detect.js test
// coverage at all before this.
//
// Building these fixtures surfaced two real, previously-unnoticed bugs
// (both fixed alongside this test):
//   - Terraform (.tf file) detection: this file's own check called
//     require('fs').readdirSync(...) inside a try/catch, but this file is
//     loaded as an ES module ('type': 'module' in package.json), where
//     require is not defined at all -- the ReferenceError was silently
//     swallowed, so a pure-Terraform project was never detected as 'iac'.
//     Fixed by importing readdirSync at the top like the file's other fs
//     calls, instead of a runtime require().
//   - Angular detection: every real Angular 2+ project depends on scoped
//     packages like '@angular/core', which don't satisfy startsWith('angular')
//     -- only ancient AngularJS 1.x used the bare 'angular' package name.
//     Fixed by switching to a substring check (matches setup.sh/setup.ps1's
//     existing, correct behavior).
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, mkdirSync, rmSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';
import { detectProjectType } from '../src/utils/detect.js';

function pkg(deps) {
  return JSON.stringify({ dependencies: deps });
}

const FIXTURES = [
  ['flutter', { 'pubspec.yaml': 'name: demo\n' }, 'mobile'],
  ['react-native', { 'package.json': pkg({ 'react-native': '^0.73.0' }) }, 'mobile'],
  ['expo', { 'package.json': pkg({ expo: '^50.0.0' }) }, 'mobile'],
  [
    'react-native-web-is-not-mobile',
    { 'package.json': pkg({ 'react-native-web': '^0.19.0', react: '^18.0.0' }) },
    'frontend-spa',
  ],
  [
    'react-native-plus-backend-monorepo',
    {
      'package.json': pkg({ 'react-native': '^0.73.0' }),
      'pom.xml': '<project></project>',
    },
    'mobile', // INVARIANT: mobile checked before fullstack
  ],
  [
    'js-frontend-plus-backend',
    { 'package.json': pkg({ react: '^18.0.0' }), 'pom.xml': '<project></project>' },
    'fullstack',
  ],
  ['electron', { 'package.json': pkg({ electron: '^28.0.0' }) }, 'desktop'],
  ['react', { 'package.json': pkg({ react: '^18.0.0' }) }, 'frontend-spa'],
  ['vue', { 'package.json': pkg({ vue: '^3.4.0' }) }, 'frontend-spa'],
  [
    'angular-scoped-packages',
    { 'package.json': pkg({ '@angular/core': '^17.0.0', '@angular/common': '^17.0.0' }) },
    'frontend-spa',
  ],
  [
    'sveltekit',
    { 'package.json': pkg({ svelte: '^4.0.0', '@sveltejs/kit': '^2.0.0' }) },
    'frontend-spa',
  ],
  ['tauri', { 'tauri.conf.json': '{}' }, 'desktop'],
  ['serverless', { 'serverless.yml': 'service: demo\n' }, 'serverless'],
  ['terraform', { 'main.tf': 'resource "null_resource" "x" {}\n' }, 'iac'],
  [
    'rust-cli',
    { 'Cargo.toml': '[package]\nname = "demo"\n\n[[bin]]\nname = "demo"\n' },
    'cli',
  ],
  ['rust-library', { 'Cargo.toml': '[package]\nname = "demo"\n' }, 'library'],
  ['go-cli', { 'go.mod': 'module demo\n', 'cmd/main.go': 'package main\n' }, 'cli'],
  ['go-backend', { 'go.mod': 'module demo\n' }, 'backend-service'],
  ['python-ml', { 'requirements.txt': 'pandas>=2.0.0\nnumpy>=1.24.0\n' }, 'data-ml'],
  [
    'python-library',
    { 'pyproject.toml': "[project]\nname = 'demo'\nbuild-backend = 'hatchling'\n" },
    'library',
  ],
  ['python-backend', { 'requirements.txt': 'click>=8.0.0\n' }, 'backend-service'],
  ['java-backend', { 'pom.xml': '<project></project>' }, 'backend-service'],
  ['empty', {}, null],
];

for (const [name, files, expected] of FIXTURES) {
  test(`detects '${expected}' for fixture: ${name}`, () => {
    const dir = mkdtempSync(join(tmpdir(), 'sdd-detect-'));
    try {
      for (const [relpath, content] of Object.entries(files)) {
        const full = join(dir, relpath);
        mkdirSync(join(full, '..'), { recursive: true });
        writeFileSync(full, content);
      }
      assert.equal(detectProjectType(dir), expected);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
}
