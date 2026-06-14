---
applyTo: "**/*.java"
---

- DTOs: records — not Lombok @Data
- Logger: @Slf4j — no System.out
- Domain entities: explicit constructors — no Lombok
- Money: BigDecimal — never double/float
- Injection: constructor — never @Autowired field
- No business logic in controllers — delegate only
