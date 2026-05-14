# 01 · Product vision

*The app is the styling agent in motion; this chapter explains what it is, who it serves, and what it deliberately isn't.*

## What Wearly is

Wearly is a **mobile-first personal styling agent**. It picks complete outfits using the user's real calendar, the day's weather, their actual wardrobe, and their personal style profile — and it explains every choice it makes.

The user-facing brand is **Wearly**. The internal description is "an agentic, evidence-informed styling system."

## Who it's for

The initial target user is **women with busy schedules** who need fast, context-aware outfit decisions for work, school, errands, travel, social events, and formal occasions.

Future versions extend to:
- men,
- children,
- family workflows including parent-managed child wardrobes.

## What it isn't

Wearly is deliberately **not**:

- a **chatbot** that returns generic suggestions from a prompt — every recommendation is structured by data and explained by a visible reasoning trail;
- a **shopping app** wearing a "styling" hat — shopping appears only when a wardrobe gap is detected;
- a **photo-feed inspiration app** — there are no influencer outfits, no infinite scroll;
- an **AI fashion oracle** that claims one correct answer — outfit choices are inherently personal, and the system says so.

## The promise

> *Outfit decisions in three seconds — reasoned through your calendar, the weather, and your real closet.*

That promise governs every design decision in the app: every screen must move the user toward that three-second outcome, or it doesn't belong.

## Where to verify

- The product brief: `Wearly_Product_Brief.md`.
- The course context that frames the academic project: `Wearly_References_and_Course_Context.md`.
- The architecture snapshot: `docs/architecture.md`.
- The product in motion: `streamlit run app.py`.

---

## Key terms

- **Agent** — a system that reads context first and recommends with a visible reasoning trail ([glossary](../docs/glossary.md)).
- **Body-positive language contract** — the runtime + documentation rule that forbids corrective vocabulary ([glossary](../docs/glossary.md)).
- **Honesty contract** — the four rules that govern every claim Wearly makes ([glossary](../docs/glossary.md)).

## Self-check

1. *(Remember)* Name the four rules of Wearly's honesty contract.
2. *(Understand)* Why does Wearly insist on the agent / chatbot distinction in its product vision?
3. *(Apply)* Pick one item on the agent-not-chatbot list and identify the screen in the running app where it shows up.

*Definitions live in the [Glossary](../docs/glossary.md). Self-check questions follow Bloom's taxonomy progression (Remember → Understand → Apply → Analyze) — the same tags used in the [Learning Graph](../docs/sims/learning-graph/index.md).*
