// Chain-integrity tests for the sdd upgrade migration table.
//
// This table is hand-mirrored from cli-python/sdd/commands/upgrade.py's
// MIGRATIONS on every release (the Node CLI is scaffolding-only and
// doesn't implement most of what it's narrating here, per this package's
// own README) -- until now, only the Python side had a test that would
// catch a broken from/to link in it. A typo here would otherwise go
// undetected by CI (node-cli-sanity only runs `node bin/sdd.js --help`)
// until a real user's `sdd upgrade` hit "No migration path found."
import test from 'node:test';
import assert from 'node:assert/strict';
import { MIGRATIONS } from '../src/commands/upgrade.js';
import { SDD_VERSION } from '../src/utils/manifest.js';

test('migration table is a connected chain ending at SDD_VERSION', () => {
  let version = null;
  for (const m of MIGRATIONS) {
    assert.equal(m.from, version, `gap in chain before v${m.to}`);
    version = m.to;
  }
  assert.equal(version, SDD_VERSION);
});

test('every migration stamps its own "to" version', () => {
  for (const m of MIGRATIONS) {
    const result = m.migrate({ project: {} });
    assert.equal(result.sdd_version, m.to);
  }
});
