# Why SDD? (Spec-Driven Development)

> "Write the spec. Then write the code. Never the other way around."

## The Problem SDD Solves

Most software projects fail not because of bad code — but because of bad requirements.
Teams build the wrong thing, discover it late, and pay enormous rework costs.
SDD inverts this: front-load clarity, back-load code.

## The 5 Core Benefits

### 1. No More "What Did We Agree On?"

Every decision is recorded in spec documents before any code exists. The BRD captures
business goals. The SRD captures functional requirements. The constitution captures
tech decisions. Anyone — engineer, product owner, new hire, AI agent — can point to
the exact document that drove a choice, months later.

### 2. AI Agents That Don't Go Off-Script

When you give an AI agent a task without a spec, it fills in the gaps with assumptions.
Those assumptions are wrong more often than not. With SDD, every TASK-NNN references a
STORY-NNN, which references an FR-NNN, which references a UC-NNN with Given/When/Then
acceptance scenarios. The agent has no room to improvise — and no excuse to.

### 3. Review at the Right Level

Business owners review the BRD (not code). Product owners review the SRD (not PRs).
Tech leads review architecture (not line diffs). Everyone reviews what they're qualified
to review — before it's built, not after.

### 4. Change Without Fear

When requirements change, you update `context.md` first. The constitution's Change Impact
Matrix shows which spec docs need updating, which tasks are invalidated, and what the AI
agent must re-examine. Change is contained and traced — not propagated silently as bugs.

### 5. Onboarding in Minutes

A new engineer, a new AI session, a new contractor — reads `CLAUDE.md`, reads the spec
docs, reads the constitution. They know the full context without asking anyone. The spec
is the institutional knowledge.

---

## Common Objections

### "It slows us down."

SDD adds ~1–2 hours of spec time per feature. It removes ~2–5 days of rework, bug
hunting, and miscommunication per feature. The math favours SDD at any meaningful
project size. The cost of a wrong implementation dwarfs the cost of thinking first.

### "We're moving too fast for specs."

If you're moving too fast to write what you're about to build, you're moving too fast.
The spec captures design thinking you'd do anyway (or should) — SDD just writes it down
so it can be reviewed, challenged, and remembered.

### "The AI is smart enough to figure it out."

AI agents are exceptionally good at executing clear instructions. They are not good at
discovering what the right instructions are — that's inference from ambiguity, which
produces confident-sounding wrong answers. The spec is how you tell the AI what to build.

### "We'll write specs after we build the prototype."

Prototypes become production. Specs written after the code describe what was built, not
what should have been built. Write specs first — even a one-paragraph BRD is better than
nothing, and `/specify` takes less than an hour.

### "Our domain changes too fast."

SDD is designed for change. The constitution's change-rules.md tracks which spec docs are
affected by each type of change. Re-running `/specify` on an amended `context.md` produces
a Constitution Amendment Summary, not a silent overwrite. Change is explicit and reviewable.

---

## The 11 Commands

SDD organizes development into commands that build on each other, each with a review gate:

```
/specify  → [GATE-1: constitution finalized]
/checklist (optional) → /validate → /analyze → /clarify
/plan-arch → /plan-hld → /plan-lld (mvp+) → /plan-adr (mvp+)
/task → /implement → /release
```

Each gate requires the previous output to be reviewed before proceeding. This is not
bureaucracy — it's quality control applied at the lowest-cost moment: before the code exists.

---

## Additional Commands

Beyond the 11-command flow, SDD includes:

| Command | When to use |
|---|---|
| `/create-context` | Build `context.md` interactively from informal notes |
| `/checklist` | Spec-quality gate: catches unmeasured NFRs, missing acceptance scenarios |
| `/bug-assess` | Structured assessment of a bug: root cause, severity, fix estimate |
| `/bug-fix` | Implement a fix from a `/bug-assess` report with regression test |
| `/taskstoissues` | Export approved tasks to GitHub Issues |

---

## Who SDD Is For

- **Teams using AI coding assistants** who want the AI to build the right thing, not just a thing
- **Startups** who've been burned by building the wrong MVP
- **Enterprises** who need traceability from business objectives to deployed code
- **Solo developers** who want to think clearly before they code and stop losing context
  between sessions

## Who SDD Is Not For

- **Pure throwaway prototypes / experiments** — use a scratchpad; don't spec it
- **Hotfixes on production incidents** — use `/bug-assess` + `/bug-fix` directly
- **One-off scripts** — just write the script; spec later when the pattern emerges

---

## Start in 5 Minutes

```bash
bash setup.sh
```

Fill in `.specify/contexts/{feature}.md`, then open your AI tool and type `/specify`.

See [QUICKSTART.md](QUICKSTART.md) for the full walkthrough.
