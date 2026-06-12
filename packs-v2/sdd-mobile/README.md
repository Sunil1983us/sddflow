# SDD Mobile Pack
## React Native · Flutter — iOS + Android

---

## What This Pack Is For
Mobile applications for iOS and Android.
Frameworks: React Native · Flutter
Deploy: App Store · Play Store · Expo

---

## How It Works — 3 Steps

### 1. Write your context (15-30 min)
Include: what the app does, screens, navigation, offline requirements,
device permissions needed, API endpoints consumed, tech stack.

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

## What SPECIFY Generates for Mobile

Constitution Part 2 extracts:
- Framework, Navigation, State, Offline Storage, CI/CD
- Core Principles: Offline-First, Accessible, Cross-Platform
- Domain Rules from your mobile context

Documents generated (pilot):
- BRD, SRD, Analyze, HLD (screen flow), UX Flow, Screen Spec, Plan, Tasks, Jira

New templates included:
- `screen-spec-template.md` — screen specifications
- `ux-flow-template.md` — user journeys

---

## Key Mobile Rules (always enforced)
- Max screen lines: 200
- No API calls in screens — service layer only
- Offline first — sync when connected
- Permissions at point of use — not on startup
- Test iOS + Android both
