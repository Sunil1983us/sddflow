# Component Specification — {Feature Name}

## References
| Source | Sections / IDs Used |
|---|---|
| srd.summary.md | {sections/IDs referenced} |
| ux-flow.summary.md | {sections/IDs referenced} |

## Component Hierarchy
```
{FeaturePage}
  └── {FeatureContainer}
        ├── {ComponentA}
        └── {ComponentB}
              └── {SharedComponent}
```

## Component Specs

### {ComponentName}
| Property | Value |
|---|---|
| Type | Page / Container / Presentational |
| State | Local / Global / None |
| Props | {list typed props} |
| Events | {list emitted events} |
| Tests | {list test scenarios} |

## Shared Components Used
> Full specs (props, events, accessibility, location) live in
> `.specify/service/component-library.md` — this table lists only which
> shared components this feature uses and any feature-specific usage
> notes. Never restate the full prop/event spec here.

| Component | Purpose in This Feature |
|---|---|
| {name} | {purpose} |

**New shared component introduced by this feature?** If a component in
the hierarchy above is intended for reuse by other features (not a
one-off page/container component), add it to
`.specify/service/component-library.md` instead of leaving it only in
this feature's hierarchy — see the living-doc-update shared block in
`specify-doc.prompt.md`.

## Approvals
| Role | Status | Date |
|---|---|---|
| {Reviewer — see this command's Review: gate in CLAUDE.md} | Pending | |

## Summary
> Lines: {N} / {SUMMARY_MAX_LINES}
## Components — {list}
## State — {global vs local}
