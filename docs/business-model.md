# Business model — who would pay for Wearly

> **Why this document exists.** SEIS 666 best-practice #6: *"if your project solved a real problem for a real organization, who's the buyer? What's the ROI?"* This page answers that without overclaiming.

---

## The problem Wearly addresses

People spend a measurable amount of time and mental energy on outfit decisions every day. Existing tools fragment the problem:

- **Weather apps** tell you the forecast — not what to wear in it.
- **Calendar apps** tell you what you're doing — not what's appropriate.
- **Closet-organizer apps** catalog items — they don't reason about them.
- **Generic styling AI tools** suggest outfits — but with no knowledge of *your* closet, *your* fit preferences, or *your* schedule, and with no audit trail.

Wearly composes those four data sources into one rule-driven recommendation with a full reasoning trail.

---

## Three potential buyers

### 1. Consumer subscription — primary path

| Aspect | Value |
|---|---|
| Who | Time-pressed professionals who own a meaningful wardrobe and want it to feel intentional |
| Price hypothesis | $4–$8 / month (validate via interviews — not claimed) |
| What they get | The Streamlit experience with cloud-persistent profile, calendar/weather integrations, wear history, and reject-and-regenerate |
| Comparable products | Cladwell ($5/mo), Acloset ($3–6/mo) — neither offers Wearly's reasoning-trail/audit-trail differentiator |

### 2. Personal-stylist tool — B2B SaaS

| Aspect | Value |
|---|---|
| Who | Independent stylists, capsule-wardrobe consultants, "uniform" coaches |
| Price hypothesis | $20–40 / month per stylist |
| What they get | A multi-client dashboard, the compact-KG export per client, the Skill package they could load into their own LLM agent |
| Differentiator | Rule citations + verified evidence categories give a stylist defensible reasoning to share with a client |

### 3. Corporate wellness / DEI tooling — niche

| Aspect | Value |
|---|---|
| Who | HR programs, return-to-office initiatives, employee-resource groups |
| Price hypothesis | License-based — not directly inferred |
| What they get | The body-positive language contract becomes a feature, not a constraint — Wearly is the rare styling tool that, by design, never frames a body as a problem |
| Differentiator | Documented contract, runtime enforcement, citation-traced inclusive-design references (see Hokka 2024 in evidence-and-references §3.4) |

---

## Why the audit trail is the moat

Every other styling app gives you a recommendation. Wearly gives you a recommendation **plus**:

- A numbered reasoning line per decision.
- Each line citing a Skill rule (e.g. `[occasion-rules#R3]`).
- Each rule traceable to an evidence category.
- Each evidence category carrying verified primary citations (Springer 2022, ACM 2017/2018, ECCV, ISO 11664-4, EUR-Lex GDPR, Cavoukian 2009).

For a paying customer this matters because:

- **Consumers** can disagree with a recommendation and have a coherent conversation back with the system (reject-and-regenerate surfaces what changed and why).
- **Stylists** can defend their advice in front of a client.
- **Corporate buyers** can audit the tool against inclusive-design and privacy standards.

The course principle "structure beats prompts" cashes out here as a real product moat: anyone can wrap GPT in a prompt; almost nobody has a rule-cited reasoning trail with verified evidence.

---

## ROI framing (illustrative, not claimed)

| Buyer | Their cost without Wearly | Their cost with Wearly |
|---|---|---|
| Consumer | ~15 min/day deciding × 5 days = 1.25 hr/week | <1 min × 5 = 5 min/week |
| Stylist | 30 min per client outfit recommendation × 20 clients = 10 hr/week | 5 min review per recommendation × 20 = 1.5 hr/week |
| Corporate program | Manual "what to wear to return-to-office" guidance | Self-service tool with body-positive contract built in |

These numbers are **illustrative** and would need user-research validation before being claimed in marketing. Wearly's documentation discipline (no invented citations, "tends to work well" not "is correct") applies here too.

---

## What this prototype is not — yet

- Not a transaction platform (no real retailer catalogs, no checkout).
- Not a multi-user product (single-user local-only data).
- Not a mobile-native app (Streamlit is mobile-responsive, but the production version would be a true iOS/Android app).
- Not a personalization engine that learns implicitly (Wearly is deliberately explicit-only; see Hu, Koren & Volinsky 2008 cited in evidence-and-references §3.8).

All three of these are paths the roadmap (`book/11-product-roadmap.md`) names as future production work, not promises this prototype delivers.

---

## See also

- `book/11-product-roadmap.md` — what future Wearly looks like
- `docs/evidence-and-references.md` — the moat in detail
- `docs/architecture.md` — the system Wearly's price would buy access to
