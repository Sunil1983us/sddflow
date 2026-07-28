# SDD Framework — Project Initializer (PowerShell)
# Usage: .\setup.ps1 [-Project <name>] [-Scope pilot|mvp|full] [-Feature <name>] [-PlanMode unified|separate] [-ReadingMode auto|summary|full]
# Run this once after copying the pack into your project directory.

param(
  [string]$Project     = "",
  [string]$Scope       = "",
  [string]$Feature     = "",
  [string]$PlanMode    = "",
  [string]$ReadingMode = ""
)

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "  SDD Framework — Setup"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

# When stdin is redirected (CI, piped input, automation), Read-Host cannot
# prompt — optional values fall back to their defaults, required ones fail fast.
$Interactive = -not [Console]::IsInputRedirected

if (-not $Project) {
  if ($Interactive) { $Project = Read-Host "Project name (e.g. my-payments-api)" }
  else { Write-Error "-Project is required when running non-interactively"; exit 1 }
}
if (-not $Feature) {
  if ($Interactive) { $Feature = Read-Host "First feature name (e.g. user-authentication)" }
  else { Write-Error "-Feature is required when running non-interactively"; exit 1 }
}
if (-not $Scope) {
  if ($Interactive) {
    Write-Host ""
    Write-Host "Scope:"
    Write-Host "  pilot  — quick prototype, minimal docs"
    Write-Host "  mvp    — production-ready"
    Write-Host "  full   — enterprise"
    $ScopeInput = Read-Host "Scope [pilot]"
    $Scope = if ($ScopeInput) { $ScopeInput } else { "pilot" }
  } else {
    $Scope = "pilot"
  }
}

if (-not $PlanMode) {
  if ($Interactive) {
    Write-Host ""
    Write-Host "Plan document style:"
    Write-Host "  unified  — One combined design.md covering architecture, diagrams,"
    Write-Host "             API design and decisions in one place."
    Write-Host "             Good for: small teams, fast delivery, single review gate."
    Write-Host ""
    Write-Host "  separate — Three focused documents reviewed one by one:"
    Write-Host "             arch.md -> hld.md -> adr.md (mvp+ only)"
    Write-Host "             Good for: larger teams, separate approvals, detailed audit trail."
    Write-Host ""
    $PlanModeInput = Read-Host "Plan mode [unified]"
    $PlanMode = if ($PlanModeInput) { $PlanModeInput } else { "unified" }
  } else {
    $PlanMode = "unified"
  }
}

if (-not $ReadingMode) {
  if ($Interactive) {
    Write-Host ""
    Write-Host "Document reading mode (token economy — see summary-rules.md):"
    Write-Host "  auto    — use each doc's .summary.md when present, fall back to the"
    Write-Host "            full document (and generate a summary) when it's missing."
    Write-Host "            Good for: almost everyone — self-heals, never stuck."
    Write-Host "  summary — always use .summary.md; warns instead of reading the full"
    Write-Host "            doc if one is missing. Good for: strict token budgets."
    Write-Host "  full    — always read the full document, every command. Good for:"
    Write-Host "            deep debugging, or migrating a project with no summaries."
    $ReadingModeInput = Read-Host "Reading mode [auto]"
    $ReadingMode = if ($ReadingModeInput) { $ReadingModeInput } else { "auto" }
  } else {
    $ReadingMode = "auto"
  }
}

Write-Host ""
Write-Host "Setting up:"
Write-Host "  Project      : $Project"
Write-Host "  Feature      : $Feature"
Write-Host "  Scope        : $Scope"
Write-Host "  Plan mode    : $PlanMode"
Write-Host "  Reading mode : $ReadingMode"
Write-Host ""

# --- Update manifest.yml ---
$ManifestPath = ".specify\manifest.yml"
if (Test-Path $ManifestPath) {
  $content = Get-Content $ManifestPath -Raw
  $content = $content -replace 'name:\s*""',                "name: `"$Project`""
  $content = $content -replace 'scope:\s*"pilot"',          "scope: `"$Scope`""
  $content = $content -replace 'feature:\s*""',             "feature: `"$Feature`""
  $content = $content -replace 'context_file:\s*""',        "context_file: `"$Feature.md`""
  $content = $content -replace 'plan_mode:\s*"unified"',    "plan_mode: `"$PlanMode`""
  $content = $content -replace 'reading_mode:\s*"auto"',    "reading_mode: `"$ReadingMode`""
  Set-Content $ManifestPath $content
  Write-Host "  [OK]  .specify\manifest.yml filled"
} else {
  Write-Error ".specify\manifest.yml not found — are you in the pack root?"
  exit 1
}

# --- Create context placeholder ---
$ContextDir  = ".specify\contexts"
New-Item -ItemType Directory -Force -Path $ContextDir | Out-Null
$ContextFile = "$ContextDir\$Feature.md"
if (-not (Test-Path $ContextFile)) {
  @"
# Context: $Feature
# Project: $Project
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
"@ | Set-Content $ContextFile
  Write-Host "  [OK]  .specify\contexts\$Feature.md created"
} else {
  Write-Host "  [OK]  .specify\contexts\$Feature.md already exists — skipped"
}

# --- Create feature output directory ---
New-Item -ItemType Directory -Force -Path ".specify\features\$Feature" | Out-Null
Write-Host "  [OK]  .specify\features\$Feature\ ready"

# --- Done ---
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "  Setup complete!"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""
Write-Host "Next steps:"
Write-Host ""
Write-Host "  1. Edit .specify\contexts\$Feature.md"
Write-Host "     Fill in: What it does, actors, flows, tech stack, NFRs"
Write-Host "     (or run /create-context to build it interactively)"
Write-Host ""
Write-Host "  2. Open this folder in your AI tool and run /specify"
Write-Host ""
Write-Host "     Claude Code  →  type:  /specify"
Write-Host "     Copilot      →  type:  /specify"
Write-Host "     Cursor       →  chat:  Read and follow .github/prompts/specify.prompt.md exactly"
Write-Host "     Windsurf     →  chat:  Run specify"
Write-Host "     Any AI       →  paste the contents of .github/prompts/specify.prompt.md"
Write-Host ""
Write-Host "  See QUICKSTART.md for the complete guide."
