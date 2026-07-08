import { existsSync, mkdirSync, writeFileSync } from 'fs';
import { dirname, join } from 'path';
import chalk from 'chalk';
import inquirer from 'inquirer';
import { detectProjectType, PROJECT_TYPES } from '../utils/detect.js';
import { validateName, assertValidName } from '../utils/validate.js';
import { patchManifest, readManifest, MANIFEST_PATH, SDD_VERSION } from '../utils/manifest.js';
import {
  recommendedPack, scaffoldPack,
  PACK_DESCRIPTIONS, ALL_PACKS, TYPE_TO_PACK,
} from '../utils/scaffold.js';

const SCOPES = ['pilot', 'mvp', 'full'];

const AI_TOOLS = [
  { name: 'Claude Code    — type /specify',                             value: 'claude-code' },
  { name: 'GitHub Copilot — type /specify',                             value: 'copilot' },
  { name: 'Cursor         — chat: Read and follow the prompt file',     value: 'cursor' },
  { name: 'Windsurf       — chat: Run specify',                         value: 'windsurf' },
  { name: 'Other / not sure',                                           value: 'other' },
];

const AI_TOOL_NEXT_STEP = {
  'claude-code': `Open this folder in Claude Code and type:  ${chalk.bold('/specify')}`,
  'copilot':     `Open in VS Code with Copilot Chat and type:  ${chalk.bold('/specify')}`,
  'cursor':      `In Cursor chat, type:\n     ${chalk.bold('Read and follow .github/prompts/specify.prompt.md exactly')}`,
  'windsurf':    `In Windsurf chat, type:  ${chalk.bold('Run specify')}`,
  'other':       `Copy ${chalk.cyan('.github/prompts/specify.prompt.md')} and paste into your AI tool`,
};

const BANNER = `
${chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}
  ${chalk.bold.cyan('SDD Framework')} ${chalk.dim(`v${SDD_VERSION}`)}
${chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')}
`;

export async function initCommand(opts) {
  console.log(BANNER);

  // ── Scaffold mode: no pack present yet ───────────────────────────────────
  let chosenPack = null;
  if (!existsSync(MANIFEST_PATH)) {
    chosenPack = await scaffoldMode(opts.type ?? null, opts.pack ?? null);
    // After scaffold, manifest.yml now exists — continue with fill mode below
  }

  // ── Fill mode: manifest.yml exists ───────────────────────────────────────

  // sdd-micro has no scope/project_type ceremony — its manifest.yml
  // template has neither key, which is how fill mode (existing manifest,
  // chosenPack unknown) detects it without tracking the pack name anywhere
  // persistent.
  let isMicro;
  if (chosenPack === 'sdd-micro') {
    isMicro = true;
  } else if (chosenPack === null) {
    const existing = readManifest() ?? {};
    isMicro = !('project_type' in existing) && !('scope' in (existing.project ?? {}));
  } else {
    isMicro = false;
  }

  // ── Project type ─────────────────────────────────────────────────────────
  let projectType = opts.type ?? null;

  if (!isMicro && !projectType) {
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
      if (confirmed) projectType = detected;
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
      when: !isMicro && (!opts.scope || !SCOPES.includes(opts.scope)),
    },
  ]);

  const projectName = opts.project  ?? answers.projectName;
  const featureName = opts.feature  ?? answers.featureName;
  const scope       = answers.scope ?? opts.scope ?? 'pilot';

  const { aiTool } = await inquirer.prompt([{
    type: 'list',
    name: 'aiTool',
    message: 'Which AI tool will you use?',
    choices: AI_TOOLS,
    pageSize: AI_TOOLS.length,
  }]);

  assertValidName(projectName, 'Project name');
  assertValidName(featureName, 'Feature name');

  console.log('');
  console.log('  Setting up:');
  console.log(`  Project : ${chalk.cyan(projectName)}`);
  if (!isMicro) console.log(`  Type    : ${chalk.cyan(projectType)}`);
  console.log(`  Feature : ${chalk.cyan(featureName)}`);
  if (!isMicro) console.log(`  Scope   : ${chalk.cyan(scope)}`);
  console.log(`  AI tool : ${chalk.cyan(aiTool)}`);
  console.log('');

  // ── Update manifest.yml ───────────────────────────────────────────────────
  const projectPatch = {
    name:         projectName,
    feature:      featureName,
    context_file: `${featureName}.md`,
  };
  const manifestPatch = {
    project:      projectPatch,
    sdd_version:  SDD_VERSION,
    ai_tool:      aiTool,
  };
  if (!isMicro) {
    projectPatch.scope = scope;
    manifestPatch.project_type = projectType;
  }
  patchManifest(manifestPatch);
  console.log(`  ${chalk.green('✓')}  ${MANIFEST_PATH} filled`);

  // ── Create context file ───────────────────────────────────────────────────
  const contextPath = join('.specify', 'contexts', `${featureName}.md`);
  mkdirSync(dirname(contextPath), { recursive: true });

  if (!existsSync(contextPath)) {
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
  const nextStep = AI_TOOL_NEXT_STEP[aiTool] ?? AI_TOOL_NEXT_STEP['other'];
  console.log('');
  console.log(chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
  console.log(`  ${chalk.bold.green('Setup complete!')}  Next steps:`);
  console.log(chalk.bold('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'));
  console.log('');
  console.log(`  1. Edit ${chalk.cyan(contextPath)}`);
  console.log('     Fill in: What it does, actors, key flows, tech stack, NFRs');
  console.log('     (or run /create-context to build it interactively)');
  console.log('');
  console.log(`  2. ${nextStep}`);
  console.log('');
  console.log('  See QUICKSTART.md for the full walkthrough.');
  console.log('');
}

/**
 * Scaffold mode — no pack in this directory.
 * Detects project type, asks which pack to copy, copies it.
 */
async function scaffoldMode(projectType, packOverride) {
  console.log(`  ${chalk.yellow('No SDD pack found in this directory.')}`);
  console.log('');

  // Detect type if not supplied
  if (!projectType) {
    process.stdout.write(chalk.dim('  Detecting project type... '));
    projectType = detectProjectType('.');
    if (projectType) {
      console.log(chalk.green(projectType));
    } else {
      console.log(chalk.yellow('not detected'));
    }
  }

  const rec = packOverride ?? recommendedPack(projectType);

  let chosenPack;

  if (packOverride) {
    chosenPack = packOverride;
    console.log(`  Pack: ${chalk.cyan(chosenPack)}  (from --pack flag)`);
  } else {
    const choices = buildPackChoices(projectType, rec);
    const { selected } = await inquirer.prompt([{
      type: 'list',
      name: 'selected',
      message: 'Which pack would you like to scaffold?',
      choices,
      pageSize: choices.length,
    }]);

    if (selected === '__all__') {
      const { all } = await inquirer.prompt([{
        type: 'list',
        name: 'all',
        message: 'Select pack:',
        choices: ALL_PACKS.map(p => ({
          name: `${p}  —  ${PACK_DESCRIPTIONS[p]}`,
          value: p,
        })),
        pageSize: ALL_PACKS.length,
      }]);
      chosenPack = all;
    } else {
      chosenPack = selected;
    }
  }

  console.log('');
  process.stdout.write(`  Scaffolding ${chalk.cyan(chosenPack)}...`);

  try {
    const n = scaffoldPack(chosenPack, '.');
    console.log(`  ${chalk.green('✓')}  ${chosenPack} scaffolded (${n} files copied)`);
    console.log('');
  } catch (err) {
    console.log('');
    console.error(chalk.red(`✗  ${err.message}`));
    process.exit(1);
  }

  return chosenPack;
}

function buildPackChoices(projectType, rec) {
  const choices = [];

  if (rec !== 'sdd-universal') {
    choices.push({
      name: `${rec}  (${PACK_DESCRIPTIONS[rec]})  ← recommended for ${projectType}`,
      value: rec,
    });
    choices.push({
      name: `sdd-universal  (${PACK_DESCRIPTIONS['sdd-universal']})`,
      value: 'sdd-universal',
    });
  } else {
    const label = projectType ? `for ${projectType}` : 'when type is unclear';
    choices.push({
      name: `sdd-universal  (${PACK_DESCRIPTIONS['sdd-universal']})  ← recommended ${label}`,
      value: 'sdd-universal',
    });
  }

  choices.push({ name: 'Choose from all packs…', value: '__all__' });
  return choices;
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
