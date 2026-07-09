# SDD Micro — Project Initializer (PowerShell)
# Usage: .\setup.ps1 [-Project <name>] [-Feature <name>]
# Run this once after copying the pack into your project directory.

param(
  [string]$Project = "",
  [string]$Feature = ""
)

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host "  SDD Micro — Setup"
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
Write-Host ""

# --- Prompt for anything not supplied (only when interactive) ---
$Interactive = [Environment]::UserInteractive -and -not [Console]::IsInputRedirected

if ([string]::IsNullOrEmpty($Project)) {
  if ($Interactive) {
    $Project = Read-Host "Project name (e.g. hello-world)"
  }
  if ([string]::IsNullOrEmpty($Project)) { $Project = "untitled-project" }
}

if ([string]::IsNullOrEmpty($Feature)) {
  if ($Interactive) {
    $Feature = Read-Host "Feature name (e.g. greeter)"
  }
  if ([string]::IsNullOrEmpty($Feature)) { $Feature = "main" }
}

# --- Validate inputs ---
# Double quotes inside a YAML double-quoted scalar produce invalid YAML.
foreach ($pair in @(@{Value=$Project; Label="Project name"}, @{Value=$Feature; Label="Feature name"})) {
  if ($pair.Value.Contains('"')) {
    Write-Error "$($pair.Label) cannot contain double-quote characters — it's written inside YAML double quotes in manifest.yml."
    exit 1
  }
}

Write-Host ""
Write-Host "Setting up:"
Write-Host "  Project : $Project"
Write-Host "  Feature : $Feature"
Write-Host ""

# --- Update manifest.yml ---
$ManifestPath = ".specify\manifest.yml"
if (Test-Path $ManifestPath) {
  $content = Get-Content $ManifestPath -Raw
  $content = $content.Replace('name: ""',         "name: `"$Project`"")
  $content = $content.Replace('feature: ""',      "feature: `"$Feature`"")
  $content = $content.Replace('context_file: ""', "context_file: `"$Feature.md`"")
  Set-Content $ManifestPath $content
  Write-Host "  [OK]  .specify\manifest.yml filled"
} else {
  Write-Error ".specify\manifest.yml not found — are you in the pack root?"
  exit 1
}

# --- Create context placeholder ---
$ContextFile = ".specify\contexts\$Feature.md"
New-Item -ItemType Directory -Force -Path (Split-Path $ContextFile -Parent) | Out-Null
if (-not (Test-Path $ContextFile)) {
  # Write template with literal placeholders, then replace using .Replace()
  # (safe against feature/project names with regex metacharacters)
  $template = @"
# Context: FEATURE_PLACEHOLDER
# Project: PROJECT_PLACEHOLDER
# Optional — you can also just describe the task to the agent in chat
# at /specify. Fill this file only if you'd rather have it written down.

## What This Does
{1-3 sentences}

## Tech Stack

| Concern | Choice |
|---|---|
| Language | {e.g. Python 3.12} |
| Framework/Library | {e.g. none} |
| Run Command | {e.g. python greet.py} |
| Test/Verify Command | {e.g. pytest, or "manual run"} |
| Storage | {e.g. none — stateless} |

## Ground Rules
{anything you want followed — optional}

## Out of Scope
{optional}
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
Write-Host "  1. (Optional) Edit .specify\contexts\$Feature.md"
Write-Host "     — or just describe the task in chat, see below"
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
Write-Host ""
