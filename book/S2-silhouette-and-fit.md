# S2 · Silhouette and fit

*Part II teaches the styling knowledge the prototype reasons over; this chapter explains how proportion-related styling enters the agent as **user-declared preference**, never as classification.*

## The concept

"Silhouette" in styling literature usually means how a garment's cut and
drape interact with the wearer's proportions. The industry convention
labels human bodies with shape categories — *hourglass, pear, apple,
inverted triangle, rectangle* — and pairs each with a small set of
proportion-related styling rules.

Wearly uses these labels, but with three constraints that make them
honest:

1. **The labels are user-declared.** The agent never analyzes images
   or measurements to infer a body shape. If a user wants to use the
   `body_shape` field, they fill it in themselves.
2. **Every field is optional with a safe default.** A blank
   `body_shape` skips every proportion-related rule. The agent's
   output never *requires* a body-shape label.
3. **The vocabulary is body-positive by contract.** No corrective
   tokens — *flaw, fix, hide, minimize, slimming, problem area* — ever
   appear in a reasoning line or in this documentation. See
   [§S8 · Body-positive framing as a discipline](S8-body-positive-framing.md).

The styling action of a shape label is small on purpose. An *hourglass*
preference, when present, surfaces lines like *"this silhouette honors
the wearer's preferred waist definition"* — not prescriptions, not
exclusions. The default behavior of the agent if the field is blank is
identical to its behavior when the field is present and the wearer
declares no proportion concerns.

## Where this knowledge comes from

The shape-category vocabulary (*hourglass / pear / apple / inverted
triangle / rectangle*) is **industry heuristic, not scientific
taxonomy.** It descends from mid-20th-century fashion-magazine and
trade-pattern literature and has no agreed academic standing. Wearly
uses it because users recognize it and because it's a compact way to
encode preferences a wearer already has — *not* because it's a valid
classification of human bodies.

The framing that makes the industry vocabulary usable without harm:

- **Hokka (2024)** documents body diversity as a known challenge for
  inclusive design and treats a small set of shape categories as a
  recognized limitation rather than a universal truth.
  ⟶ [References [7]](../docs/references.md). The Wearly framing —
  *"if you've shared a body-shape preference"* rather than *"based on
  your body type"* — is a direct expression of that limitation.

## What Wearly deliberately does not do

- It does not infer shape from photos. There is no image classifier,
  no body-detection model, no measurement extraction.
- It does not enforce body-shape rules. A blank field skips every
  related rule; a populated field surfaces preference-aware notes but
  never excludes a garment.
- It does not use corrective vocabulary. The body-positive language
  contract is a runtime check, not just a documentation aspiration.
- It does not claim the shape vocabulary is a taxonomy. The vocabulary
  is a *proxy* for proportion-related preferences; the user is the
  final reviewer.

## How Wearly applies this

| Where | What happens |
|---|---|
| **Rule pack** | [`fit-silhouette-rules.md`](../skills/wearly-styling-agent/fit-silhouette-rules.md) — R1 (body-positive contract), R2 (optional fields), R8 (measurement framing) |
| **Runtime code** | `fit_tool.fit_alignment_notes()`, `fit_tool.check_reasoning_for_forbidden_language()` |
| **Agent step** | Step 2 (load profile) and Step 5 (outfit construction) |
| **Where it surfaces** | Fit-alignment notes inside the reasoning trail; the regenerate banner when the profile changes mid-session |
| **Part I chapter** | [Chapter 06 · Fit-profile logic](06-fit-profile-logic.md) |
| **MicroSim** | *(none yet — candidate for a future sim that shows which rules fire when each fit-profile field is set vs. blank)* |

---

## Key terms

- **Fit profile** — optional, user-declared preferences. Every field has a safe default. See [Glossary](../docs/glossary.md).
- **Body shape (preference)** — a user-declared proportion preference, never inferred from images. See [Glossary](../docs/glossary.md).
- **Body-positive language contract** — the runtime + documentation rule that forbids corrective vocabulary. See [§S8](S8-body-positive-framing.md).

## Self-check

1. *(Remember)* List three forbidden tokens from the body-positive language contract.
2. *(Understand)* Why does Wearly call `body_shape` a *preference* rather than a *classification*?
3. *(Apply)* A user leaves `body_shape` blank. Which proportion-related rules fire, and which don't?
