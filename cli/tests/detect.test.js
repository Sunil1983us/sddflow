// Regression test for detectProjectType()'s Terraform (.tf file) detection.
//
// detect.js used to call `require('fs').readdirSync(...)` inside a try/catch
// -- but this file is loaded as an ES module ('type': 'module' in
// package.json), where `require` is not defined at all. The ReferenceError
// was silently swallowed by the catch, so this branch always returned false:
// a pure-Terraform project with no Pulumi.yaml/cdk.json was never detected
// as 'iac'. Fixed by importing readdirSync at the top like the rest of the
// file's fs calls, instead of a runtime require().
import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, rmSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';
import { detectProjectType } from '../src/utils/detect.js';

test('a directory containing a .tf file is detected as iac', () => {
  const dir = mkdtempSync(join(tmpdir(), 'sdd-detect-tf-'));
  try {
    writeFileSync(join(dir, 'main.tf'), '');
    assert.equal(detectProjectType(dir), 'iac');
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test('a directory with no recognizable markers detects nothing', () => {
  const dir = mkdtempSync(join(tmpdir(), 'sdd-detect-empty-'));
  try {
    assert.equal(detectProjectType(dir), null);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
