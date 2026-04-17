# Orchestrator â€” Layer 2

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
1. Truth          â†’  grounded in source material?
2. Mission Fit    â†’  Community / Environment / Transparency?
3. Tone & Dignity â†’  calm, grounded, on-brand?
4. CTA            â†’  clear, appropriate, non-extractive?
```

| Failure | Action |
|---|---|
| Check 1 fails | STOP â€” do not proceed |
| Check 2 fails | SAVE_DRAFT â€” escalate |
| Check 3 fails | CONSTRAIN â€” reduce complexity |
| Check 4 only  | CONSTRAIN â€” flag for revision |
| All pass      | PROCEED |

---

## Autonomy Rule

Agents operate autonomously by default. However:
- Autonomy does not override truth or alignment
- Autonomy is bounded by directive + brand checks

---

## Escalation Triggers

Escalate (save draft â†’ log â†’ notify user) when:
- Truth cannot be verified
- Mission fit is unclear
- Failure cannot be self-corrected
- System risks fabricating or misrepresenting

