# SDD Framework — Project Initializer (PowerShell)
# Usage: .\setup.ps1 [-Project <name>] [-Scope pilot|mvp|full] [-Feature <name>] [-Type <project-type>]
# Run this once after copying the pack into your project directory.

param(
  [string]$Project = "",
  [string]$Scope   = "",
  [string]$Feature = "",
  [string]$Type    = ""
)

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "  SDD Framework — Setup"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

# --- Auto-detect project type ---
function Detect-ProjectType {
  $root = "."

  # Mobile (Flutter/Dart) — before fullstack to avoid misclassifying RN + backend monorepo
  if (Test-Path "$root/pubspec.yaml") { return "mobile" }

  if (Test-Path "$root/package.json") {
    try {
      $pkg  = Get-Content "$root/package.json" -Raw | ConvertFrom-Json
      $deps = @()
      if ($pkg.dependencies)    { $deps += ($pkg.dependencies    | Get-Member -MemberType NoteProperty).Name }
      if ($pkg.devDependencies) { $deps += ($pkg.devDependencies | Get-Member -MemberType NoteProperty).Name }
      $depStr = $deps -join " "

      # Mobile (React Native / Expo) — before fullstack
      if ($depStr -match 'react-native|expo') { return "mobile" }

      # Fullstack: JS frontend + separate backend (only after mobile ruled out)
      if ((Test-Path "$root/pom.xml") -or (Test-Path "$root/build.gradle") -or (Test-Path "$root/go.mod")) {
        return "fullstack"
      }

      if ($depStr -match 'electron')                              { return "desktop" }
      if ($depStr -match '\breact\b|\bvue\b|angular|svelte|next|nuxt') { return "frontend-spa" }
    } catch {}
  }

  if ((Test-Path "$root/tauri.conf.json") -or (Test-Path "$root/src-tauri/tauri.conf.json")) { return "desktop" }
  if (Test-Path "$root/serverless.yml") { return "serverless" }
  if ((Test-Path "$root/template.yaml") -and ((Get-Content "$root/template.yaml" -Raw) -match 'AWSTemplateFormatVersion')) { return "serverless" }
  if ((Get-ChildItem "$root/*.tf" -ErrorAction SilentlyContinue) -or (Test-Path "$root/Pulumi.yaml") -or (Test-Path "$root/cdk.json")) { return "iac" }

  if (Test-Path "$root/Cargo.toml") {
    $cargo = Get-Content "$root/Cargo.toml" -Raw
    if ($cargo -match '\[\[bin\]\]') { return "cli" } else { return "library" }
  }

  if (Test-Path "$root/go.mod") {
    if (Test-Path "$root/cmd") { return "cli" } else { return "backend-service" }
  }

  if ((Test-Path "$root/pyproject.toml") -or (Test-Path "$root/requirements.txt")) {
    $pyDeps = ""
    if (Test-Path "$root/requirements.txt") { $pyDeps += Get-Content "$root/requirements.txt" -Raw }
    if (Test-Path "$root/pyproject.toml")   { $pyDeps += Get-Content "$root/pyproject.toml"   -Raw }
    $pyDeps = $pyDeps.ToLower()
    if ($pyDeps -match 'pandas|torch|tensorflow|sklearn|keras|jax|xgboost|lightgbm') { return "data-ml" }
    $isLib = ($pyDeps -match 'install_requires|build-backend') -and
             (-not (Test-Path "$root/main.py")) -and
             (-not (Test-Path "$root/app"))     -and
             (-not (Test-Path "$root/src/app"))
    if ($isLib) { return "library" }
    return "backend-service"
  }

  if ((Test-Path "$root/pom.xml") -or (Test-Path "$root/build.gradle") -or (Test-Path "$root/build.gradle.kts")) {
    return "backend-service"
  }

  return ""
}

if ($Type) {
  $ProjectType = $Type
  Write-Host "  Project type (from -Type): $ProjectType"
} else {
  Write-Host "  Detecting project type..."
  $Detected = Detect-ProjectType
  if ($Detected) {
    Write-Host "  Detected: $Detected"
    Write-Host ""
    $TypeInput = Read-Host "  Project type [$Detected]"
    $ProjectType = if ($TypeInput) { $TypeInput } else { $Detected }
  } else {
    Write-Host "  Could not auto-detect. Supported types:"
    Write-Host "    backend-service  frontend-spa  mobile  fullstack"
    Write-Host "    cli  data-ml  serverless  library  iac  desktop"
    Write-Host ""
    do { $ProjectType = Read-Host "  Project type" } while (-not $ProjectType)
  }
}
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
Write-Host "  Type    : $ProjectType"
Write-Host "  Feature : $Feature"
Write-Host "  Scope   : $Scope"
Write-Host ""

# --- Update manifest.yml ---
# Use .Replace() (literal string substitution) instead of -replace (regex) so
# that special characters in $Project/$Feature/$ProjectType — including $, \,
# and regex metacharacters — are treated as data, not as pattern or
# replacement metacharacters.
$ManifestPath = ".specify\manifest.yml"
if (Test-Path $ManifestPath) {
  $content = Get-Content $ManifestPath -Raw
  $content = $content.Replace('name: ""',             "name: `"$Project`"")
  $content = $content.Replace('scope: "pilot"',       "scope: `"$Scope`"")
  $content = $content.Replace('feature: ""',          "feature: `"$Feature`"")
  $content = $content.Replace('context_file: ""',     "context_file: `"$Feature.md`"")
  $content = $content.Replace('project_type: "auto"', "project_type: `"$ProjectType`"")
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
  # Write template with literal placeholders, then replace using .Replace()
  # (safe against feature/project names with regex metacharacters)
  $template = @"
# Context: FEATURE_PLACEHOLDER
# Project: PROJECT_PLACEHOLDER
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
"@
  $template = $template.Replace('FEATURE_PLACEHOLDER', $Feature)
  $template = $template.Replace('PROJECT_PLACEHOLDER', $Project)
  Set-Content $ContextFile $template
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
