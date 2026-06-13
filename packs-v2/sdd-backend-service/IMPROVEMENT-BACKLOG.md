# Improvement Backlog — Phase 3 (Deferred)
# Items identified during the framework review that are valuable but
# out of scope for the current fix pass. Pick these up as needed.

---

## OBS-1 — Observability / SLO Depth
security-design.md and resilience.md cover alerting at a high level.
Not yet covered: SLO definitions (e.g. error budget, burn-rate alerts),
dashboards-as-code (Grafana JSON checked into repo), and a standard
"golden signals" template (latency, traffic, errors, saturation) per
service. Add an `observability-template.md` if this pack is used for
services with formal SLOs.

## OPS-8 — Kubernetes Manifests
docker-config-template.md covers docker-compose for local/dev. No
equivalent `k8s/` template (Deployment, Service, HPA, NetworkPolicy,
ConfigMap/Secret refs) exists for clusters that go straight to
Kubernetes. Add a `k8s-manifest-template.md` referencing the same
Containerization rules in constitution.md Part 1.

## SEC-8 — Data Classification Depth
data-model-template.md §6 (added in this pass) gives a starting
classification/PII/retention table. A full data-governance pass
(field-level lineage, cross-border transfer rules, anonymization/
pseudonymization strategy for non-prod environments) is deferred.

## FW-9 — License + Versioning Policy
No template captures third-party license compliance (e.g. disallowed
licenses for dependencies) or a semantic-versioning policy for the
service's own API. Add to security-design.md §2 (SCA) or a new
`compliance-template.md` if needed.

## AI-9 — Prompt-Caching / Token-Cost Strategy
summary-rules.md (AI-2) keeps per-command reads small, but there is no
guidance on structuring prompts to take advantage of provider-side
prompt caching (e.g. keeping CLAUDE.md / constitution.md as a stable
prefix across a session). Consider documenting a recommended prompt
ordering once usage data is available.

## QA-2 — Test Data Management
qa-testcases-template.md defines test cases but not a strategy for
seed/test data management across environments (mock vs test vs prod-like
staging). Consider a `test-data-strategy.md` for mvp+/full.

---
*This file is created once per pack. Add pack-specific deferred items
below this line as they are identified.*
