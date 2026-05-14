# Glossary

> A single place to look up every domain term Wearly uses. The glossary
> unifies vocabulary across the two layers of the project: the
> **styling-agent prototype** (the working app) and the **Intelligent
> Book** (its learning and reference companion). Definitions are short
> on purpose — each entry links to the chapter or rule file where the
> term is introduced in context.
>
> Inspired by the `glossary-generator` skill in
> [dmccreary/claude-skills](https://github.com/dmccreary/claude-skills),
> which the Level-2 intelligent-textbook framework expects.

---

## A

**Agent** — A system that reads context first and recommends with a visible
reasoning trail. Distinct from a *chatbot*, which responds to a free-text
prompt. See [Chapter 1 · Product vision](../book/01-vision.md) and
[Chapter 3 · Agent workflow](../book/03-agent-workflow.md).

**Agentic loop** — The reject-and-regenerate cycle: the user pushes back on
a recommendation, the agent re-runs with the rejection recorded as a
constraint, and the new reasoning trail surfaces what changed. See
[Chapter 3 § Reject & regenerate](../book/03-agent-workflow.md).

## B

**Blend note** — A short, body-positive line that explains how two or more
pieces work together (e.g., *"the camel sweater warms the navy trouser"*).
Surfaced inside the reasoning trail.

**Bloom level** — Cognitive level a concept sits at: Remember → Understand →
Apply → Analyze. Every node in the learning graph is tagged with one of
these. See [the learning graph](sims/learning-graph/index.md).

**Body-positive language contract** — A runtime + documentation rule that
forbids tokens like *flaw, fix, hide, minimize, correct, problem area,
slimming, shameful*. Enforced in `fit_tool.check_reasoning_for_forbidden_language()`
and in `tests/test_documentation_integrity.py`. See
[Chapter 6 · Fit-profile logic](../book/06-fit-profile-logic.md).

**Body shape (preference)** — A *user-declared proportion preference*
(hourglass, pear, apple, inverted triangle, rectangle). Industry heuristic,
not scientific taxonomy. Wearly never infers it from images. See
[evidence-and-references § Body-shape framing](evidence-and-references.md).

## C

**Calendar context** — Upcoming event metadata read by Step 1 of the
workflow. Drives occasion classification. Falls back to *casual* if no
events are scheduled. See [Chapter 7](../book/07-calendar-weather-context.md).

**Citation chip** — The small `[occasion-rules#R8]`-style tag appended to a
reasoning line. Renders as a clickable chip in the UI; resolves via
`rule_refs.py` to the named rule heading.

**Color tier** — One of *+8* (great), *+4* (okay), or *−10* (avoid) — the
three-value scoring scale Wearly uses for color-against-skin-tone judgments.
See [`color-coordination-rules.md`](../skills/wearly-styling-agent/color-coordination-rules.md).

## E

**Evidence categories** — The nine source categories every Wearly rule
traces back to (recommender systems, outfit compatibility, color harmony,
body-shape/fit, XAI, human-centered AI, wardrobe management, personalization,
privacy). See [evidence-and-references](evidence-and-references.md).

## F

**Favorite stores** — A locally-stored list of retailers the user has
saved. Personalizes the wardrobe-gap "where to look" suggestions without
transmitting anything outside the device. See
[Chapter 8](../book/08-shopping-gap-logic.md).

**Fit profile** — Optional, user-declared preferences: `body_shape`,
`modesty_preference`, `comfort_needs`, `style_goals`, `highlight_features`,
`balance_areas`. Every field is optional; defaults are safe. See
[Chapter 6](../book/06-fit-profile-logic.md).

**Freshness score** — A 0–1 value combining a frequency penalty and a
recency penalty, with a **0.4 floor** so a much-loved piece is never
exiled from the rotation. See
[`wear-history-rules.md`](../skills/wearly-styling-agent/wear-history-rules.md).

## G

**Gap (wardrobe gap)** — A required piece type the user does not own for
the current occasion. Surfaced as a *descriptive*, never-promotional
shopping suggestion. See [Chapter 8](../book/08-shopping-gap-logic.md).

## H

**Honesty contract** — Four rules that govern every claim Wearly makes:
styling is not exact science; body-positive language is non-negotiable; no
fabricated citations; the user is the final reviewer. See
[evidence-and-references § The honesty contract](evidence-and-references.md).

## K

**Knowledge graph (runtime)** — *See* **Reasoning Graph**. The earlier
name "knowledge graph" was retired on display surfaces because
McCreary's framework uses *knowledge graph* and *concept graph*
interchangeably for the *reader's* concept DAG; we now call Wearly's
runtime entity graph the Reasoning Graph to avoid the clash. File
paths and the JSON source are unchanged.

**Reasoning Graph** — The wardrobe entities and typed relations the
agent reasons over at runtime (User → CalendarEvent →
OutfitRecommendation → WardrobeItem → ShoppingSuggestion / Feedback).
Modeled in `graph/graph.json` with the schema in
[`graph/schema.md`](../graph/schema.md). Distinct from the **Learning
Graph** (the reader's concept DAG).

## L

**Learning graph** — A directed acyclic graph (DAG) of the 28 concepts a
reader needs to understand the system. Categories follow Bloom's
progression. See [the learning graph](sims/learning-graph/index.md).

**Level-2 intelligent textbook** — Per
[Dan McCreary's framework](https://dmccreary.github.io/intelligent-textbooks/),
a book whose structure is driven by a concept-dependency graph and that
ships MicroSims, glossary, FAQ, references, and Bloom-tagged concepts.
Wearly is built to this level.

## M

**MicroSim** — A small p5.js / vis-network interactive that lives in
`docs/sims/<name>/` alongside its `index.md`. Wearly currently ships four:
color harmony, freshness, knowledge graph, learning graph.

## O

**Occasion tag** — One of five canonical labels Wearly classifies any
event into: *work, gym, dinner, formal, casual*. See
[`occasion-rules.md`](../skills/wearly-styling-agent/occasion-rules.md).

## P

**Profile hash** — A short hash of the merged fit profile, used by the UI
to detect when the user has edited their profile mid-session and surface a
"regenerate" banner. See [Chapter 6](../book/06-fit-profile-logic.md).

## Q

**Qualified gap** — A gap that survives a second check: the user owns
nothing of the required type *and* the missing piece is plausibly
shoppable for this occasion. Prevents noisy suggestions for niche events.

## R

**Regenerate banner** — A small UI affordance shown when the merged profile
hash changes, prompting the user to re-run the agent against the updated
inputs. See [Chapter 6](../book/06-fit-profile-logic.md).

**Reject & regenerate** — The agentic loop where the user rejects a
recommendation and the agent re-runs with the rejection recorded as an
exclusion. The reasoning trail shows what changed. See
[Chapter 3](../book/03-agent-workflow.md).

**Required pieces** — The minimum type-set an occasion needs (work needs
top + bottom; gym needs activewear; formal needs a dress; etc.). See
[`occasion-rules.md`](../skills/wearly-styling-agent/occasion-rules.md).

**Result-dict contract** — The single boundary between the agent and the
UI: a Python dict with `steps`, `recommendation`, `reasoning`, `gaps`,
`color_score`, `weather`, `event`, `profile`. See
[`docs/architecture.md`](architecture.md).

**Rule citation (R\<N\>)** — An `R1`, `R2`, … heading inside a Skill rule
file. Referenced from runtime reasoning via the slug `<pack>#R<N>` (e.g.
`occasion#R8`). Registry: `rule_refs.py`.

## S

**Seven-step workflow** — Wearly's canonical reasoning order: determine
occasion → load profile → check weather → filter wardrobe → build outfit
→ check gaps → score color. See [Chapter 3](../book/03-agent-workflow.md).

**Skill package** — `skills/wearly-styling-agent/` — eight rule files plus
a `SKILL.md` that follows the agentskills.io specification.

**Skin-tone palette** — One of three named palettes (*warm olive, cool
fair, deep warm*) that Wearly's color-score formula reads from. See
[`color-coordination-rules.md`](../skills/wearly-styling-agent/color-coordination-rules.md).

## T

**Tradeoff record** — A short structured note attached to a recommendation
when the agent made a non-obvious choice (e.g., picked a slightly less
fresh item because the color score was much higher). Surfaced in the
reasoning trail.

## W

**Wardrobe filtering** — Step 4 of the workflow: narrow the full closet
to the candidate pool that matches occasion tags + season + availability +
prior rejection exclusions. See
[`wardrobe-filtering-rules.md`](../skills/wearly-styling-agent/wardrobe-filtering-rules.md).

**Wardrobe gap** — *See `Gap`.*

**Wear history** — Per-item `worn_count` and `last_worn_date`, written when
the user confirms an outfit. Feeds the freshness score. See
[`wear-history-rules.md`](../skills/wearly-styling-agent/wear-history-rules.md).

**Weather context** — Live Open-Meteo data, with a seasonal fallback when
the user is offline. Drives layering thresholds and season tags. See
[Chapter 7](../book/07-calendar-weather-context.md).

**Wishlist** — A locally-stored list of items the user wants to acquire
next, with optional priority and `linked_gap` fields. Used by
`infer_wishlist_taste()` to bias selection toward acquired-taste signals.

---

*Pattern follows `glossary-generator` from
[dmccreary/claude-skills](https://github.com/dmccreary/claude-skills). Add a
term when it's used in at least two places (a chapter and a rule, or two
chapters) and a reader can't infer its meaning from context.*
