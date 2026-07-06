import { existsSync } from 'fs';
import chalk from 'chalk';
import { readManifest, patchManifest, MANIFEST_PATH, SDD_VERSION } from '../utils/manifest.js';

// Version migration table — describes what changed between pack versions.
// Extend this when releasing a new pack version.
// Each migrate() stamps its own "to" version so chained upgrades stay truthful.
const MIGRATIONS = [
  {
    from: null,          // null = pre-versioning (v1.x, no sdd_version field)
    to:   '2.0.0',
    description: 'Initial versioned release',
    notes: [
      'Added sdd_version field to manifest.yml for upgrade tracking',
      'setup.sh/setup.ps1 rewritten to use js-yaml — eliminates injection bugs',
      'Input validation: project/feature names with " are now rejected early',
      'Detection order fix: mobile (react-native) now checked before fullstack',
      'Cross-reference comment added to all 3 detection locations',
    ],
    migrate: (manifest) => {
      // Add sdd_version if missing — no other structural changes needed
      manifest.sdd_version = '2.0.0';
      return manifest;
    },
  },
  {
    from: '2.0.0',
    to:   '2.7.0',
    description: 'Content release — no manifest schema changes',
    notes: [
      '/change command: type-aware change requests at any SDLC stage',
      '/jira-push: progressive Jira export (Epic/Story/Task/CHG)',
      'Review gates: three modes (chat / local / jira) — Jira now optional',
      "sdd review approve --local also updates the doc's Confluence page",
      'setup.sh/setup.ps1 safe in non-interactive runs (CI, piped input)',
      'Re-copy the pack (or run sdd init over it) to pick up new prompt files',
    ],
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.0';
      return manifest;
    },
  },
  {
    from: '2.7.0',
    to:   '2.7.1',
    description: 'Content release — no manifest schema changes',
    notes: [
      '/create-context: Endpoints and NFRs now get a proposed ' +
      'scope-appropriate starting default, marked ' +
      '(SUGGESTED DEFAULT — edit or confirm), instead of always ' +
      'falling back to [MISSING — ask user]',
      'Re-copy the pack (or run sdd init over it) to pick up the ' +
      'updated .github/prompts/create-context.prompt.md',
    ],
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.1';
      return manifest;
    },
  },
  {
    from: '2.7.1',
    to:   '2.7.3',
    description: 'Version scheme unified — one number instead of two',
    notes: [
      'sdd_version no longer tracks a separate content/schema counter ' +
      '— it now always matches the installed sddflow package version ' +
      '(sdd --version), so this file and the CLI never show two ' +
      'different numbers again',
      'No framework content changed in this step beyond the version ' +
      'scheme itself',
    ],
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.3';
      return manifest;
    },
  },
  {
    from: '2.7.3',
    to:   '2.7.4',
    description: 'Content release — no manifest schema changes',
    notes: [
      '/change: when a CR fundamentally broadens or narrows what a ' +
      'feature IS (not just a detail change) — e.g. a fixed ' +
      'pain.001→pacs.008 converter generalized into a generic ISO ' +
      '20022 parser — the agent now recommends renaming the feature ' +
      'slug to match, and will perform the rename (directory, ' +
      'manifest.yml, context file) if you approve',
      "changeset-template.md: added a 'Feature renamed' row to §1 " +
      'Change Description',
      'Re-copy the pack (or run sdd init over it) to pick up the ' +
      'updated .github/prompts/change.prompt.md and ' +
      'changeset-template.md',
    ],
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.4';
      return manifest;
    },
  },
  {
    from: '2.7.4',
    to:   '2.7.5',
    description: 'Version alignment only — no Node CLI changes',
    notes: [
      'This release fixed a path-traversal gap in the Python CLI only ' +
      '(sdd confluence / sdd cr / sdd jira, which have no Node ' +
      'equivalent commands) — nothing in the Node CLI changed. Version ' +
      'bumped to keep sdd_version aligned across both CLIs.',
    ],
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.5';
      return manifest;
    },
  },
  {
    from: '2.7.5',
    to:   '2.7.6',
    description: 'Content release — new .specify/service/ directory',
    notes: [
      'data-model.md, security-design.md, and the API design section of ' +
      'design.md are now living, service-level documents instead of being ' +
      'regenerated per feature — they live at .specify/service/{doc}.md ' +
      'and get extended/amended by every feature after the first one that ' +
      'needs them, instead of each feature getting its own independent ' +
      '(and eventually contradictory) copy',
      'docs/runbook/local-setup.md, docs/openapi.yaml, and ' +
      'docker-compose.yml/k8s manifests now have explicit ' +
      'check-before-regenerate guidance for the same reason',
      'If you already have per-feature data-model.md/security-design.md ' +
      'files from before this release, they are NOT automatically moved ' +
      'or merged — reconcile them into .specify/service/ yourself the ' +
      'next time you run /specify-doc data-model (or security)',
      'Re-copy the pack (or run sdd init over it) to pick up the updated ' +
      '.github/prompts/specify-doc.prompt.md and plan-design.prompt.md',
    ],
    migrate: (manifest) => {
      manifest.sdd_version = '2.7.6';
      return manifest;
    },
  },
];

export async function upgradeCommand() {
  console.log('');
  console.log(chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
  console.log(`  ${chalk.bold.cyan('SDD Framework')} — upgrade`);
  console.log(chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
  console.log('');

  if (!existsSync(MANIFEST_PATH)) {
    console.error(chalk.red(`✗  ${MANIFEST_PATH} not found — run from the pack root directory.`));
    process.exit(1);
  }

  const manifest = readManifest();
  const currentVersion = manifest?.sdd_version ?? null;

  if (currentVersion === SDD_VERSION) {
    console.log(chalk.green(`  ✓  Already at v${SDD_VERSION} — nothing to do.`));
    console.log('');
    return;
  }

  console.log(`  Current version : ${chalk.yellow(currentVersion ?? 'pre-versioning (v1.x)')}`);
  console.log(`  Target version  : ${chalk.green(SDD_VERSION)}`);
  console.log('');

  // Find applicable migrations
  const pending = MIGRATIONS.filter(m => {
    if (currentVersion === null && m.from === null) return true;
    return m.from === currentVersion;
  });

  if (pending.length === 0) {
    console.log(chalk.yellow('  No migration path found for your current version.'));
    console.log('  You may need to manually update — see CHANGELOG.md.');
    console.log('');
    return;
  }

  for (const migration of pending) {
    console.log(chalk.bold(`  Migrating → v${migration.to}: ${migration.description}`));
    for (const note of migration.notes) {
      console.log(`    ${chalk.dim('•')} ${note}`);
    }
    console.log('');

    // Apply migration
    let m = readManifest();
    m = migration.migrate(m);
    patchManifest({ sdd_version: m.sdd_version }, MANIFEST_PATH);
    console.log(`  ${chalk.green('✓')}  ${MANIFEST_PATH} updated to v${migration.to}`);
    console.log('');
  }

  const finalVersion = readManifest()?.sdd_version;
  if (finalVersion !== SDD_VERSION) {
    console.log(chalk.yellow(`  Now at v${finalVersion} — run sdd upgrade again to continue to v${SDD_VERSION}.`));
    console.log('');
  }

  console.log(chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
  console.log(`  ${chalk.bold.green('Upgrade complete!')}  Review the changes above and`);
  console.log('  update any prompt files that reference old command names.');
  console.log(chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
  console.log('');
}
