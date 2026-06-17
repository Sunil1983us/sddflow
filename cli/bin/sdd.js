#!/usr/bin/env node
import { program } from 'commander';
import { createRequire } from 'module';
import { initCommand } from '../src/commands/init.js';
import { upgradeCommand } from '../src/commands/upgrade.js';

const require = createRequire(import.meta.url);
const { version } = require('../package.json');

program
  .name('sdd')
  .description('SDD Framework CLI — Spec-Driven Development')
  .version(version);

program
  .command('init')
  .description('Initialize an SDD pack in the current project directory')
  .option('-p, --project <name>',  'Project name')
  .option('-f, --feature <name>',  'First feature name')
  .option('-s, --scope <scope>',   'Scope: pilot | mvp | full', 'pilot')
  .option('-t, --type <type>',     'Project type (auto-detected if omitted)')
  .action(initCommand);

program
  .command('upgrade')
  .description('Migrate manifest.yml to the current pack version')
  .action(upgradeCommand);

program.parse();
