---
applyTo: "**/controller/**"
---

- Delegate only — zero business logic
- Inject inbound port interface — not service class
- All endpoints versioned: /api/v1/
- Mandatory headers validated at entry
- Return correct HTTP status codes
