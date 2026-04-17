# Orchestrator  Layer 2

This package is the **decision-making layer** of the Autonomous Systems agent architecture.

> *"You are the bridge between intention and action."*

---

## Responsibilities

| Module | Role |
|---|---|
| `router.py` | Load directives, validate structure, build execution plan, route to executor |
| `brand_alignment.py` | 4-dimension BAE check before any public-facing output |
| `output_classes.py` | Define and enforce the 4 output classes and their risk tolerances |
| `error_handler.py` | Self-correction retries, draft saving, escalation |

---

## Brand Alignment Engine (BAE)

Run **in order** before any `CLIENT_FACING_DRAFT` or `PUBLIC_FACING_PUBLISHED` output:

```
1. Truth            grounded in source material?
2. Mission Fit      Community / Environment / Transparency?
3. Tone & Dignity   calm, grounded, on-brand?
4. CTA              clear, appropriate, non-extractive?
```

| Failure | Action |
|---|---|
| Check 1 fails | STOP  do not proceed |
| Check 2 fails | SAVE_DRAFT  escalate |
| Check 3 fails | CONSTRAIN  reduce complexity |
| Check 4 only  | CONSTRAIN  flag for revision |
| All pass      | PROCEED |

---

## Autonomy Rule

Agents operate autonomously by default. However:
- Autonomy does not override truth or alignment
- Autonomy is bounded by directive + brand checks

---

## Escalation Triggers

Escalate (save draft  log  notify user) when:
- Truth cannot be verified
- Mission fit is unclear
- Failure cannot be self-corrected
- System risks fabricating or misrepresenting
