# OpenAPI Skeleton
# Feature: {Feature Name}
> Generated at: /implement (full scope) | Input: api-spec.summary.md
> Save as: docs/openapi.yaml (this file documents how to derive it)

---

## Mapping from api-spec.md → openapi.yaml

| api-spec.md section | openapi.yaml location |
|---|---|
| Base URL | `servers[0].url` |
| Authentication | `components.securitySchemes` + `security` |
| Common Headers | `components.parameters` (referenced via `$ref` on each operation) |
| Each Endpoint | `paths.{path}.{method}` |
| Request/Response bodies | `components.schemas` |
| Error Response Format | `components.schemas.Error` |
| Error Codes table | enum values on `Error.properties.errorCode` |

---

## Skeleton

```yaml
openapi: 3.0.3
info:
  title: "{Service Name}"
  version: "1.0.0"
servers:
  - url: "{protocol}://{host}/api/v1"
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
  parameters:
    CorrelationId:
      name: X-Correlation-Id
      in: header
      required: true
      schema: { type: string, format: uuid }
  schemas:
    Error:
      type: object
      properties:
        errorCode: { type: string }
        message: { type: string }
        timestamp: { type: string, format: date-time }
        traceId: { type: string }
security:
  - bearerAuth: []
paths:
  /{resource}:
    post:
      summary: "{purpose}"
      parameters:
        - $ref: '#/components/parameters/CorrelationId'
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                {field}: { type: string }
      responses:
        '202':
          description: Accepted
        '400':
          description: Validation error
          content:
            application/json:
              schema: { $ref: '#/components/schemas/Error' }
```

---

## Validation
- [ ] Every endpoint in api-spec.md present in openapi.yaml
- [ ] Every error code in api-spec.md §7 present in `Error.errorCode` enum
- [ ] Lint with `npx @redocly/cli lint docs/openapi.yaml` (or equivalent) — zero errors

---
*Generated from: api-spec.summary.md*
