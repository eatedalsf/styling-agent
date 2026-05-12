# Privacy guidelines

What the Wearly skill is allowed to do with user data.

## R1 — Minimum-necessary access

The skill reads only the data it needs to produce an outfit:

- Calendar: **the next upcoming event**, not the whole calendar.
- Wardrobe: items + the owner profile block.
- Weather: lat/lon → public weather; no user identifier sent.

The skill must **never** read:

- Calendar events outside the planning window.
- Wardrobe items not eligible for the current occasion (other than for gap detection).
- Files outside the project root.

## R2 — No third-party transmission

The skill is allowed exactly one external call: weather. Any other network access (analytics, telemetry, model hosting) is **forbidden** in the prototype and must be opt-in in production.

## R3 — No corrective body language

The skill must not output language that frames body features as flaws. See `fit-silhouette-rules.md` R1 for the contract.

## R4 — Honest gaps over forced fits

If a required piece is missing, surface a gap. Never fabricate an item that isn't in the wardrobe. Never lie about the outfit's completeness.

## R5 — User pushback is authoritative

When the user rejects an item with a reason, the agent **must** honor the rejection AND surface the reason in the reasoning trail. The agent does not argue with the user about taste.

## R6 — No data retention beyond the session

In the prototype, the only persistent state is `wardrobe.json` and (when Phase 4 ships) `wear_history.json`. Rejection state is session-local and evaporates when the page closes.

Production retention policies are documented in `book/10-privacy-security.md`.

## R7 — Children's data

If the skill is ever invoked in a family context with a child profile, stricter rules apply (see `Wearly_Product_Brief.md` §2 and §3):

- No external network calls at all on child-only sessions.
- No suggestions to buy.
- Parent-managed only.

A future version of this skill will refuse to run in a child-profile context until these guardrails are in place.

## R8 — Refusal triggers

The skill should **refuse** and surface a clear message when:

- A user requests fashion advice that depends on body image judgment (e.g., language framed as needing correction).
- A user requests that the skill exfiltrate their own data.
- A caller tries to use the skill for any task outside the Scope Boundary in `SKILL.md`.

Refusal is part of the skill, not a failure mode.

---

## Source basis

**Primary category:** Privacy and personal data (`docs/evidence-and-references.md` §3.9).
**Secondary:** Human-centered AI / personalization (§3.6).
**Current basis:** Privacy-by-design principles + minimum-necessary access. Wearly's production data-handling roadmap aligns with publicly available frameworks (GDPR, CCPA, privacy-by-design) — see `book/10-privacy-security.md`.
**Pending verification:** Specific GDPR article numbers, privacy-by-design framework citation with verified date (Ann Cavoukian), and direct URLs for the Microsoft AI Guidelines for Human-AI Interaction and Google PAIR Guidebook.
