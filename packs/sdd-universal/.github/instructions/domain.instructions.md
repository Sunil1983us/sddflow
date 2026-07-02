---
applyTo: "**/domain/**,**/core/**,**/model/**,**/models/**"
---

- Business logic lives here — not in controllers, handlers, or UI
- No framework or infrastructure imports — pure language constructs only
- Entities immutable where the language allows (records / final / frozen dataclasses / const)
- External systems reached through port interfaces only — never direct calls
- One responsibility per class/module — split if it does two things
