# SDD Frontend SPA Pack
## React · Vue · Angular · Svelte

---

## What This Pack Is For
Single page applications, component-based UI, state management.
Frameworks: React · Vue · Angular · Svelte
Deploy: Docker/Nginx · Vercel · Netlify · S3

---

## How It Works — 3 Steps

### 1. Write your context (15-30 min)
Include: what the app does, user flows, components needed,
state management approach, API contracts (if known), tech stack.

### 2. Fill manifest (2 min)
```yaml
project:
  name: "My App"
  scope: "pilot"
  feature: "my-feature"
  context_file: "my-feature.md"
```

### 3. Run — same 6 verbs as all packs

---

## What SPECIFY Generates for Frontend

Constitution Part 2 extracts:
- Framework, Styling, State Management, Testing, E2E
- Core Principles: Component-First, Accessible, Performant
- Domain Rules from your UX/business context

Documents generated (pilot):
- BRD, SRD, Analyze, HLD (component diagram), UX Flow, Plan, Tasks, Jira

New templates included:
- `ux-flow-template.md` — user journeys
- `component-spec-template.md` — component hierarchy

---

## Key Frontend Rules (always enforced)
- Max component lines: 150
- No API calls in components — service layer only
- No inline styles
- Every component has paired test
- axe-core a11y on every component test
