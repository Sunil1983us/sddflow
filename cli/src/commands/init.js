import { existsSync, mkdirSync, writeFileSync } from 'fs';
import { dirname, join } from 'path';
import chalk from 'chalk';
import inquirer from 'inquirer';
import { detectProjectType, PROJECT_TYPES } from '../utils/detect.js';
import { validateName, assertValidName } from '../utils/validate.js';
import { patchManifest, MANIFEST_PATH, SDD_VERSION } from '../utils/manifest.js';

const SCOPES = ['pilot', 'mvp', 'full'];

const BANNER = `
${chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}
  ${chalk.bold.cyan('SDD Framework')} ${chalk.dim(`v${SDD_VERSION}`)}
${chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}
`;

export async function initCommand(opts) {
  console.log(BANNER);

  if (!existsSync(MANIFEST_PATH)) {
    console.error(chalk.red(`✗  ${MANIFEST_PATH} not found — run from the pack root directory.`));
    process.exit(1);
  }

  // ── Project type ─────────────────────────────────────────────────────────
  let projectType = opts.type ?? null;

  if (!projectType) {
    process.stdout.write(chalk.dim('  Detecting project type... '));
    const detected = detectProjectType('.');
    if (detected) {
      console.log(chalk.green(detected));
      const { confirmed } = await inquirer.prompt([{
        type: 'confirm',
        name: 'confirmed',
        message: `  Use detected type ${chalk.cyan(detected)}?`,
        default: true,
      }]);
      if (confirmed) {
        projectType = detected;
      }
    } else {
      console.log(chalk.yellow('not detected'));
    }

    if (!projectType) {
      const { chosen } = await inquirer.prompt([{
        type: 'list',
        name: 'chosen',
        message: '  Project type:',
        choices: PROJECT_TYPES,
        pageSize: PROJECT_TYPES.length,
      }]);
      projectType = chosen;
    }
  }

  // ── Interactive prompts ───────────────────────────────────────────────────
  const answers = await inquirer.prompt([
    {
      type: 'input',
      name: 'projectName',
      message: 'Project name:',
      default: opts.project,
      when: !opts.project,
      validate: v => validateName(v, 'Project name'),
    },
    {
      type: 'input',
      name: 'featureName',
      message: 'First feature name:',
      default: opts.feature,
      when: !opts.feature,
      validate: v => validateName(v, 'Feature name'),
    },
    {
      type: 'list',
      name: 'scope',
      message: 'Scope:',
      choices: [
        { name: 'pilot  — quick prototype, minimal docs', value: 'pilot' },
        { name: 'mvp    — production-ready (+ api-spec, data-model, LLD, ADR)', value: 'mvp' },
        { name: 'full   — enterprise (+ resilience, investigation, security-design)', value: 'full' },
      ],
      default: SCOPES.indexOf(opts.scope ?? 'pilot'),
      when: !opts.scope || !SCOPES.includes(opts.scope),
    },
  ]);

  const projectName = opts.project  ?? answers.projectName;
  const featureName = opts.feature  ?? answers.featureName;
  const scope       = answers.scope ?? opts.scope ?? 'pilot';

  // Validate CLI-supplied values (inquirer validates interactive ones)
  assertValidName(projectName, 'Project name');
  assertValidName(featureName, 'Feature name');

  console.log('');
  console.log('  Setting up:');
  console.log(`  Project : ${chalk.cyan(projectName)}`);
  console.log(`  Type    : ${chalk.cyan(projectType)}`);
  console.log(`  Feature : ${chalk.cyan(featureName)}`);
  console.log(`  Scope   : ${chalk.cyan(scope)}`);
  console.log('');

  // ── Update manifest.yml via js-yaml (no string injection possible) ────────
  patchManifest({
    project: {
      name:         projectName,
      scope,
      feature:      featureName,
      context_file: `${featureName}.md`,
    },
    project_type: projectType,
    sdd_version:  SDD_VERSION,
  });
  console.log(`  ${chalk.green('✓')}  ${MANIFEST_PATH} filled`);

  // ── Create context file ───────────────────────────────────────────────────
  const contextPath = join('.specify', 'contexts', `${featureName}.md`);
  mkdirSync(dirname(contextPath), { recursive: true });

  if (!existsSync(contextPath)) {
    // Generate content directly — no placeholder substitution needed
    writeFileSync(contextPath, contextTemplate(featureName, projectName));
    console.log(`  ${chalk.green('✓')}  ${contextPath} created`);
  } else {
    console.log(`  ${chalk.dim('·')}  ${contextPath} already exists — skipped`);
  }

  // ── Create feature output directory ──────────────────────────────────────
  const featureDir = join('.specify', 'features', featureName);
  mkdirSync(featureDir, { recursive: true });
  console.log(`  ${chalk.green('✓')}  ${featureDir}/ ready`);

  // ── Done ──────────────────────────────────────────────────────────────────
  console.log('');
  console.log(chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
  console.log(`  ${chalk.bold.green('Setup complete!')}  Next steps:`);
  console.log(chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
  console.log('');
  console.log(`  1. Edit ${chalk.cyan(contextPath)}`);
  console.log('     Fill in: What it does, actors, key flows, tech stack, NFRs');
  console.log('     (or run /create-context to build it interactively)');
  console.log('');
  console.log('  2. Open in your AI tool and run /specify');
  console.log('');
  console.log(`     ${chalk.bold('Claude Code')}  →  /specify`);
  console.log(`     ${chalk.bold('Copilot')}      →  /specify`);
  console.log(`     ${chalk.bold('Cursor')}        →  Read and follow .github/prompts/specify.prompt.md`);
  console.log(`     ${chalk.bold('Windsurf')}     →  Run specify`);
  console.log('');
  console.log('  See QUICKSTART.md for the full walkthrough.');
  console.log('');
}

function contextTemplate(featureName, projectName) {
  return `# Context: ${featureName}
# Project: ${projectName}
# Fill this file, then run /specify (or /create-context to build it interactively).

## What This Does
{describe the feature in 2-3 sentences}

## Actors
{who triggers or benefits from this feature?}

## Key Flows
{describe 2-3 main user journeys}

## Integrations
{list any external systems, APIs, or databases}

## Business Rules
{any constraints, validation rules, or compliance requirements}

## Tech Stack
{language, framework, database, cache, CI/CD — fill what you know}

## Non-Functional Requirements
{performance targets, availability, security level}

## Out of Scope
{explicitly list what this feature does NOT cover}

## Open Questions
{anything unclear that needs a decision}
`;
}
