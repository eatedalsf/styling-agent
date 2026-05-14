# 10 · Privacy & security

Wearly handles calendar events, location data, wardrobe photos (in production), measurements, and personal preferences. This chapter documents how those are handled today and how they would be handled in production.

## Today (prototype)

| Data | Where it lives | Who sees it |
|---|---|---|
| Calendar events | `calendar_events.json` (mock) | Local only |
| Location | Hard-coded Minneapolis lat/lon | Sent to Open-Meteo API |
| Weather | Live Open-Meteo call | Open-Meteo (no account) |
| Wardrobe | `wardrobe.json` | Local only |
| Profile (name, body shape, skin tone, prefs) | `wardrobe.json` `owner` block | Local only |
| Rejection history (in-session) | Streamlit session state | Local only, evaporates on page close |

The privacy strip on the home and the privacy paragraph on the profile screen are both honest:

> Your calendar, weather, wardrobe, and profile data are used only for outfit planning in this prototype. No accounts. No third parties.

The single external network call is to Open-Meteo with a lat/lon (no user identifier). Open-Meteo's privacy policy is permissive; the call is unauthenticated and has no session.

## Production path

### Authentication

- **Single sign-on via Apple / Google.** No password storage. OAuth tokens kept server-side, encrypted at rest.
- **No email-password fallback** in v1 — keeps the credential attack surface minimal.
- The current `Sign in with Apple / Google (coming soon)` placeholder on the profile screen is exactly the future flow.

### Data residency

- **Personal data minimized.** Body measurements, modesty preferences, etc. are *optional* — Wearly works with whatever the user shares.
- **Encryption at rest.** All per-user data encrypted with per-user keys.
- **Regional storage.** EU users' data stays in the EU; US users' data stays in the US.

### Calendar integrations

- **OAuth scopes minimum-necessary.** Read-only `calendar.events.readonly`. No write access. No metadata access.
- **Revocable consent.** A single tap in Settings revokes access; cached events purged.
- **Per-event encryption** so a database breach doesn't expose calendar contents.

### Location

- **Opt-in geolocation.** Default: user-picked city.
- **Coarse precision.** City-level, never block-level.
- **Not retained.** Location is used for the weather call, not stored as a user attribute.

### Photos (wardrobe builder)

- **Stored encrypted, deletable.** A user can purge their entire wardrobe with one tap.
- **Server-side background removal.** Original photo is processed once, then the original is purged; only the white-background variant is retained.
- **Never reused for training.** Wardrobe photos are inputs to the user's own product, not a corpus.

### Third parties

- **Open-Meteo** — anonymous lat/lon for weather. No user data.
- **Apple / Google** — only as identity providers under OAuth.
- **No analytics SDKs** in v1. If analytics is ever added, it's first-party event collection only.
- **No ad networks. Ever.**

### Children

- **Family profiles are a special case.** A parent-managed child profile is a separate data class with stricter retention rules and explicit parental consent flows. Designing this is part of the family workflow scope, not an afterthought.

## Threat model (concise)

| Threat | Mitigation |
|---|---|
| Lost device | Per-device tokens; sign-out revokes |
| Stolen credentials | OAuth refresh tokens revocable per-session |
| Database breach | Per-user encryption; minimum-necessary scopes |
| Prompt injection (if LLM is added later) | Trust boundary at tool calls; never forward calendar text into a model that has tool-execution privileges |
| Social engineering | No password reset flow in v1 — fewer paths for an attacker to use |

## Where to verify

- The privacy strip: `app.py` → footer of `_render_home()`.
- The profile privacy note: `app.py` → end of `_render_profile()`.
- The single external call: `weather_tool.py`.
- The product brief commitments: `Wearly_Product_Brief.md`.

---

## Key terms

- **Privacy stance** — minimum-necessary access, no third parties, no implicit data collection ([glossary](../docs/glossary.md)).
- **Honesty contract** — the four rules that govern every claim, including privacy claims ([glossary](../docs/glossary.md)).

## Self-check

1. *(Remember)* Name the four GDPR articles Wearly's privacy stance maps to.
2. *(Understand)* Why does Wearly cite GDPR if the prototype doesn't transmit data?
3. *(Apply)* A user asks to delete all their Wearly data. Describe the exact steps in the prototype today.

*Definitions live in the [Glossary](../docs/glossary.md). Self-check questions follow Bloom's taxonomy progression (Remember → Understand → Apply → Analyze) — the same tags used in the [Learning Graph](../docs/sims/learning-graph/index.md).*
