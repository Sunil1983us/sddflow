import { existsSync } from 'fs';
import chalk from 'chalk';
import { readManifest, patchManifest, MANIFEST_PATH, SDD_VERSION } from '../utils/manifest.js';

// Version migration table — describes what changed between pack versions.
// Extend this when releasing a new pack version.
const MIGRATIONS = [
  {
    from: null,
    to:   '2.0.0',
    description: 'Initial versioned release',
    notes: [
      'Added sdd_version field to manifest.yml for upgrade tracking',
      'setup.sh/setup.ps1 rewritten to use js-yaml — eliminates injection bugs',
      'Input validation: project/feature names with " are now rejected early',
      'Detection order fix: mobile (react-native) now checked before fullstack',
    ],
    migrate: (m) => { m.sdd_version = '2.0.0'; return m; },
  },
  {
    from: '2.0.0',
    to:   '2.1.0',
    description: 'Document-level review gates + PR automation',
    notes: [
      'sdd review submit/check/apply/status commands added',
      'sdd pr create command added',
      'document_reviews + pr_automation sections added to integrations.yml',
    ],
    migrate: (m) => { m.sdd_version = '2.1.0'; return m; },
  },
  {
    from: '2.1.0',
    to:   '2.2.0',
    description: 'Code review gate (/pre-review + /address-review)',
    notes: [
      '/pre-review agent command added — run before PR creation',
      '/address-review agent command added — handles human PR comments',
      'code_review section added to integrations.yml',
    ],
    migrate: (m) => { m.sdd_version = '2.2.0'; return m; },
  },
  {
    from: '2.2.0',
    to:   '2.3.0',
    description: 'Explicit reading_mode enforcement',
    notes: [
      'reading_mode field added to manifest.yml (auto/summary/full)',
      'All prompts now check reading_mode before reading feature docs',
    ],
    migrate: (m) => { m.sdd_version = '2.3.0'; return m; },
  },
  {
    from: '2.3.0',
    to:   '2.4.0',
    description: '/specify-uc use case specification command',
    notes: [
      '/specify-uc inserted between /specify-brd and /specify-srd',
      'use-cases.md template added with actor registry, UC details, traceability',
      'SRD now derives FR-NNN from UC paths',
    ],
    migrate: (m) => { m.sdd_version = '2.4.0'; return m; },
  },
  {
    from: '2.4.0',
    to:   '2.5.0',
    description: '19 SDLC review findings fixed',
    notes: [
      'change-rules.md dependency chain updated (use-cases between brd and srd)',
      'task.prompt.md: EP-NNN exception paths generate TC-NNN test cases',
      'security design: full STRIDE/DREAD methodology',
      'CLAUDE.md: /checklist mandatory for mvp+',
    ],
    migrate: (m) => { m.sdd_version = '2.5.0'; return m; },
  },
  {
    from: '2.5.0',
    to:   '2.6.0',
    description: '/change command + 20 stakeholder template improvements',
    notes: [
      '/change command added — type-aware sequential change request system',
      'changeset-template.md added to .specify/templates/',
      '20 template fixes: approvals tables, BUFFER story, CVSS column, BRD investment summary',
      '/create-context: feature-hint header (# specify: sentence) added',
      'SDLC-COMPLETE-GUIDE.md and CHANGE-GUIDE.md rewritten',
    ],
    migrate: (m) => { m.sdd_version = '2.6.0'; return m; },
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

  console.log(chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
  console.log(`  ${chalk.bold.green('Upgrade complete!')}  Review the changes above and`);
  console.log('  update any prompt files that reference old command names.');
  console.log(chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
  console.log('');
}
