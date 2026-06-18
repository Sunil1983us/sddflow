# SDD Framework — Project Initializer (PowerShell)
# Usage: .\setup.ps1 [-Project <name>] [-Scope pilot|mvp|full] [-Feature <name>]
# Run this once after copying the pack into your project directory.

param(
  [string]$Project = "",
  [string]$Scope   = "",
  [string]$Feature = ""
)

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "  SDD Framework — Setup"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

if (-not $Project) { $Project = Read-Host "Project name (e.g. my-payments-api)" }
if (-not $Feature) { $Feature = Read-Host "First feature name (e.g. user-authentication)" }
if (-not $Scope) {
  Write-Host ""
  Write-Host "Scope:"
  Write-Host "  pilot  — quick prototype, minimal docs"
  Write-Host "  mvp    — production-ready"
  Write-Host "  full   — enterprise"
  $ScopeInput = Read-Host "Scope [pilot]"
  $Scope = if ($ScopeInput) { $ScopeInput } else { "pilot" }
}

Write-Host ""
Write-Host "Setting up:"
Write-Host "  Project : $Project"
Write-Host "  Feature : $Feature"
Write-Host "  Scope   : $Scope"
Write-Host ""

# --- Update manifest.yml ---
$ManifestPath = ".specify\manifest.yml"
if (Test-Path $ManifestPath) {
  $content = Get-Content $ManifestPath -Raw
  $content = $content -replace 'name:\s*""',         "name: `"$Project`""
  $content = $content -replace 'scope:\s*"pilot"',   "scope: `"$Scope`""
  $content = $content -replace 'feature:\s*""',      "feature: `"$Feature`""
  $content = $content -replace 'context_file:\s*""', "context_file: `"$Feature.md`""
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
