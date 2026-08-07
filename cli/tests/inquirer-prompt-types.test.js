// Regression test for a real bug: src/commands/init.js and upgrade.js
// hardcoded `type: 'list'` in every inquirer.prompt() call. Dependabot bumped
// inquirer 9.2.0 -> 14.0.2 (merged into main, inherited via this branch's
// merge), which dropped the legacy 'list' prompt type in favor of 'select'
// -- inquirer.prompt() throws UnknownPromptTypeError at runtime for any
// unregistered type string. This broke every interactive `sdd init` for
// anyone not passing every single CLI flag (there's no --ai-tool flag to
// skip that one prompt), and none of the existing automated tests caught
// it -- they only exercise migration-chain logic, never a real prompt call.
//
// This test extracts every `type: '...'` string actually used in an
// inquirer.prompt() call across the source tree and asserts it's a member
// of inquirer's own currently-registered prompt types -- read directly from
// the installed inquirer package, not a hardcoded list here, so a future
// inquirer upgrade that renames/drops a type this codebase depends on fails
// this test immediately instead of only surfacing as a runtime crash for a
// real user.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'fs';
import { join } from 'path';
import { fileURLToPath } from 'url';
import inquirer from 'inquirer';

const __dirname = fileURLToPath(new URL('.', import.meta.url));
const srcCommandsDir = join(__dirname, '..', 'src', 'commands');

function findPromptTypesInFile(path) {
  const content = readFileSync(path, 'utf8');
  const types = [];
  const re = /inquirer\.prompt\(/g;
  let m;
  while ((m = re.exec(content))) {
    // Scan forward from this inquirer.prompt( call to its matching closing
    // paren, tracking bracket depth, and collect every type: '...' inside
    // that span -- a single inquirer.prompt([...]) call can (and does, in
    // this codebase) ask multiple questions with different types.
    let depth = 1;
    let i = m.index + m[0].length;
    const start = i;
    while (depth > 0 && i < content.length) {
      if (content[i] === '(') depth++;
      else if (content[i] === ')') depth--;
      i++;
    }
    const block = content.slice(start, i);
    const typeRe = /type:\s*'([^']+)'/g;
    let tm;
    while ((tm = typeRe.exec(block))) {
      types.push(tm[1]);
    }
  }
  return types;
}

test("every inquirer.prompt() type: string is a real, currently-registered inquirer prompt type", () => {
  const registeredTypes = new Set(Object.keys(inquirer.prompt.prompts));
  assert.ok(registeredTypes.size > 0, 'sanity check: inquirer should expose at least one registered prompt type');

  const files = readdirSync(srcCommandsDir)
    .filter(f => f.endsWith('.js'))
    .map(f => join(srcCommandsDir, f));

  let checked = 0;
  for (const file of files) {
    const types = findPromptTypesInFile(file);
    for (const type of types) {
      checked++;
      assert.ok(
        registeredTypes.has(type),
        `${file} uses inquirer type '${type}', which is not registered in ` +
        `the installed inquirer version. Registered types: ` +
        `${[...registeredTypes].join(', ')}`
      );
    }
  }
  // If this drops to 0, the regex above stopped matching real usage
  // (e.g. the calling convention changed) and the test would pass
  // vacuously without actually checking anything -- fail loudly instead.
  assert.ok(checked > 0, 'expected to find at least one inquirer.prompt() type: usage to check');
});
