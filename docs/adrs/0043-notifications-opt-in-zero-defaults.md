# ADR-0043: Notifications are opt-in with zero defaults

- **Date**: 2026-05-28
- **Status**: accepted
- **Deciders**: Lead engineer, Pedagogical architect, UX lead
- **Phase**: 8 (Frontend UX)

## Context

The dominant product-led-growth pattern for web/mobile apps is to
prompt the user to enable notifications during onboarding, then send
daily reminders that drive return-traffic.

That pattern is misaligned with our cohort (anxious adults preparing
for immigration) and our principles (ADR-0042). Specifically:

- A 7 a.m. "you have a drill block!" push wakes a user who slept
  through it on purpose to recover before work.
- A 3-day-streak-protection ping shames the user for being
  human.
- Aggregated push behaviour from the product trains the user to
  *swipe to dismiss* — degrading any later high-signal notification
  (a real mock-exam appointment reminder).

The Phase 8 design pre-commits to "zero defaults"; this ADR encodes
the rule.

## Decision

All notification surfaces ship with the default state **OFF**. The
opt-in surfaces, all reachable from `Settings → Notifications`:

- Daily reminder at a user-chosen time.
- Mock-exam scheduled reminder.
- Streak-protection ping after 3 days of inactivity (this one is
  doubly-gated: user must explicitly opt-in *and* the settings page
  recommends against it).

Copy rules:

- No urgency language: banned tokens include `lost!`, `behind!`,
  `don't miss`, `hurry`.
- No fear/anxiety triggers: no countdown clocks, no "you're falling
  behind" framing.
- No social comparison: notifications never reference other users.
- Reviewed in CI by a lint rule scanning all message catalogs for
  banned patterns.

Web push only; we do not implement SMS or marketing email.

## Consequences

- DAU lift from notification re-engagement is forfeited. Acceptable
  given the calm principle.
- Onboarding does not include a notification-permission prompt at
  all. The prompt only appears if the user enables a notification
  surface in Settings.
- The notification settings page leads with the recommendation to
  leave them off. This is unusual; it is intentional.
- Reversing this is high-cost: defaults that opt users in to push
  are a trust violation we would have to apologise for.

## Related

- ADR-0042 (no gamification), ADR-0044 (a11y)
- `phase8_think.md §11`, `phase8_design.md §6, §14.3`
