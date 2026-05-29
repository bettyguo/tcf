# Phase 9 pedagogy calibration plot

> Planner-projected min-skill at horizon (x) vs simulated median
> min-skill at horizon (y). The dashed y=x line marks perfect
> calibration; the gate is ±10pp on P(success) (see 
> `tests/pedagogy/launch_audit.py`).

```mermaid
%%{init: {'theme':'neutral'}}%%
quadrantChart
    title Planner projection vs simulated median (NCLC units)
    x-axis 'projected_min (planner)' --> 12
    y-axis 'simulated median' --> 12
    quadrant-1 'Planner under-promises'
    quadrant-2 'Planner under-promises (high)'
    quadrant-3 'Planner over-promises (low)'
    quadrant-4 'Planner over-promises'
    solid B1 target NCLC7: [0.592, 0.596]
    solid B1 target NCLC9: [0.600, 0.599]
    uneven target NCLC7: [0.592, 0.596]
    strong B2 target NCLC9: [0.758, 0.762]
    aggressive B1 target C2: [0.592, 0.588]
    short runway target NCLC7: [0.508, 0.508]
    low budget target NCLC7: [0.483, 0.479]
    already at target: [0.817, 0.815]
    heritage production gap: [0.617, 0.615]
    reception only weakness: [0.600, 0.602]
    ee bottleneck only: [0.683, 0.687]
    eo bottleneck only: [0.683, 0.686]
```

## Per-cohort table

| Cohort | kind | target | planner_projected | simulated_median | P(success) | gate |
|---|---|---|---|---|---|---|
| solid_B1_target_NCLC7 | realistic | 7 | 7.10 | 7.15 | 1.00 | ✅ |
| solid_B1_target_NCLC9 | honest_refusal | 9 | 7.20 | 7.19 | 0.00 | ✅ |
| uneven_target_NCLC7 | realistic | 7 | 7.10 | 7.15 | 1.00 | ✅ |
| strong_B2_target_NCLC9 | realistic | 9 | 9.10 | 9.15 | 1.00 | ✅ |
| aggressive_B1_target_C2 | honest_refusal | 11 | 7.10 | 7.06 | 0.00 | ✅ |
| short_runway_target_NCLC7 | honest_refusal | 7 | 6.10 | 6.10 | 0.00 | ✅ |
| low_budget_target_NCLC7 | honest_refusal | 7 | 5.80 | 5.75 | 0.00 | ✅ |
| already_at_target | trivial | 9 | 9.80 | 9.78 | 1.00 | ✅ |
| heritage_production_gap | realistic | 7 | 7.40 | 7.39 | 1.00 | ✅ |
| reception_only_weakness | realistic | 7 | 7.20 | 7.22 | 1.00 | ✅ |
| ee_bottleneck_only | realistic | 8 | 8.20 | 8.24 | 1.00 | ✅ |
| eo_bottleneck_only | realistic | 8 | 8.20 | 8.23 | 1.00 | ✅ |
