# Component Specification — {Feature Name}
> Input: srd.summary.md + ux-flow.summary.md

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
| Component | From | Purpose |
|---|---|---|
| {name} | {library/local} | {purpose} |

## Summary
> Lines: {N} / {SUMMARY_MAX_LINES}
## Components — {list}
## State — {global vs local}
