---
applyTo: "**/controller/**,**/controllers/**,**/routes/**,**/api/**,**/handlers/**,**/cli/**,**/cmd/**,**/commands/**"
---

- Entry points delegate only — zero business logic (controllers, route handlers, CLI commands, lambda handlers alike)
- Inject the inbound port/service interface — not a concrete class
- Validate and normalise input at the boundary; reject early with a clear message
- HTTP APIs: versioned paths (/api/v1/), correct status codes, error body = errorCode + message + timestamp — no stack traces
- CLIs/jobs: meaningful exit codes (0 success, non-zero failure), errors to stderr, machine-readable output behind a flag where useful
- Never log request/response bodies or PII — metadata only (constitution Logging rules)
