# How to Write Your Context
# This is the ONLY input the agent needs.
# Constitution Part 2 is generated FROM this file.

## Don't Want to Write This Yourself? Use /create-context

Not everyone can fill out a structured context file from scratch — and
that's fine. Run `/create-context` instead:

1. Paste whatever you have — rough notes, an email, a requirements doc,
   even half-formed bullet points. Any format.
2. The agent maps it onto the sections below, fills in what it can, and
   gives you a plain-language checklist of what's still missing.
3. Answer what you can (partial answers OK, "not sure" is fine for
   technical questions — the architect decides later at /plan-arch).
4. The agent saves the finished `.specify/contexts/{feature}.md` — the
   same file /specify reads either way.

Your original raw notes can optionally be kept as
`.specify/contexts/{feature}.raw.md` (reference only — not read by any
other command) so you can re-run `/create-context` later with more detail
(e.g. when scope upgrades from pilot to mvp/full).

If you're comfortable writing the structured file directly, skip
`/create-context` and follow the template below.

## What to Include

### 1. What the system does (2-3 sentences)
### 2. Actors — who uses or calls it
### 3. Key flows — step by step (happy path + key unhappy paths)
### 4. Integrations — what external systems are involved
### 5. Tech stack — what technologies you are using
### 6. NFRs — performance, availability, scalability targets
### 7. Constraints — regulatory, security, business rules
### 8. Out of scope — what is explicitly excluded

## What the Agent Extracts for Constitution

From your tech stack section:
  Language, Framework, Database, Cache, Messaging,
  Deployment, CI/CD, Testing approach → fills Tech Stack table

From your constraints section:
  Business rules → Domain Rules
  "never do" items → Never Do list
  Compliance requirements → Core Principles

## Template

# System Context — {Service Name}
# Version: 1.0 | Date: {date}

## What This Does
{2-3 sentences}

## Actors
| Actor | Type | Role |
|---|---|---|

## Tech Stack
| Concern | Choice |
|---|---|
| Language | {e.g. Java 21} |
| Framework | {e.g. Spring Boot 3.x} |
| Database | {e.g. PostgreSQL 15} |
| Deployment | {e.g. Kubernetes} |
| CI/CD | {e.g. Jenkins} |
| Testing | {e.g. JUnit 5 + Testcontainers} |
| ... add all relevant |

## Key Flows
### Happy Path
1. {step}
2. {step}

### Unhappy Path (if applicable)
1. {step}

## Integrations
| System | Direction | Purpose |
|---|---|---|

## NFRs
| Category | Requirement |
|---|---|
| Performance | |
| Availability | |

## Constraints
- {business rule}
- {regulatory requirement}

## Out of Scope
- {item}

## CHANGELOG
### v1.0 — {date}
- Initial version
