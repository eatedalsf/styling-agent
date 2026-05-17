# Frequently asked questions

> Top questions readers (and SEIS 666 reviewers) ask after their first
> pass through the book. Grouped by topic. Each answer links to the
> chapter or rule that goes deeper.
>
> Pattern follows the `faq-generator` skill in
> [dmccreary/claude-skills](https://github.com/dmccreary/claude-skills).
> Add a question here when it's been asked twice.

---

## Product

### What is the Intelligent Book vs. the app?

**Wearly's Intelligent Book is the learning and reference companion
for the styling-agent prototype.** The app shows what Wearly does;
the book explains how and why it reasons that way. The app is a
Streamlit prototype you run locally; the book is the MkDocs-built
site you're reading now, with chapters, a glossary, a learning graph,
a reasoning graph, and interactive MicroSims. The two are meant to be
read together — the prototype demonstrates the agent in action; the
book is the structured explanation behind every line of its reasoning.

### What is Wearly, in one sentence?

An evidence-informed, body-positive personal styling agent that reads
your calendar, weather, and closet, then produces a single outfit
recommendation with a visible reasoning trail you can argue with.
See [Chapter 1](../book/01-vision.md).

### Who is Wearly for?

A single user managing a real wardrobe, who wants the 15-minute
"what do I wear today" decision to feel grounded rather than guessed.
The prototype is single-user and local-only.

### Is Wearly a real product or a course project?

It's a working prototype built for SEIS 666 (Digital Transformation
with AI) at the University of St. Thomas. The code runs, the
documentation is the Intelligent Book you're reading, and the rule
citations trace to verified sources. The roadmap chapter outlines
what a production version would add.

### What does Wearly NOT do?

It doesn't analyze body photos, infer your body shape, sell anything,
talk to third-party servers (except the unauthenticated Open-Meteo
weather call), or judge your wardrobe. See
[Chapter 10 · Privacy](../book/10-privacy-security.md).

## Agent reasoning

### Why call it an "agent" and not a "chatbot"?

A chatbot waits for free-text and responds. An agent reads context
*first* — your calendar, the weather, your closet, your fit profile —
then recommends with a visible reasoning trail. The whole product is
designed around that distinction. See [Chapter 1](../book/01-vision.md)
and [Chapter 3](../book/03-agent-workflow.md).

### What are the "seven steps"?

Determine occasion → load profile → check weather → filter wardrobe →
build outfit → check gaps → score color. Every recommendation runs
this loop and surfaces a sentence (or two) per step in the reasoning
panel. See [Chapter 3](../book/03-agent-workflow.md).

### What happens when I reject an outfit?

The rejection is recorded as an exclusion for the next run, the agent
re-runs all seven steps with that constraint, and the new reasoning
trail surfaces what changed. This is the *reject-and-regenerate* loop —
arguably the most "agentic" moment in the product. See
[`wardrobe-filtering-rules.md` R5](../skills/wearly-styling-agent/wardrobe-filtering-rules.md).

### Why does each reasoning line carry a tag like `[occasion-rules#R8]`?

That's a citation chip. It resolves via `rule_refs.py` to a named
heading inside a Skill rule file, so you (and a reviewer) can trace any
sentence in the output back to a specific rule. The pattern is
documented in
[evidence-and-references § 6a](evidence-and-references.md).

## Personalization

### Do I have to fill out a fit profile?

No. Every field on the fit profile is optional and has a safe default.
If you leave `body_shape` blank, no body-shape-related rule fires; the
agent still works. See [Chapter 6](../book/06-fit-profile-logic.md).

### How does Wearly decide what's "fresh"?

The freshness score combines a frequency penalty (how often you wear it)
and a recency penalty (how recently). The score is floored at **0.4** so
a much-loved piece is never pushed out of rotation. See
[`wear-history-rules.md`](../skills/wearly-styling-agent/wear-history-rules.md).

### Does Wearly track what I look at, scroll past, or hover over?

No. It only uses *explicit* feedback: the reject button, the "wear this
outfit today" confirmation, and the editable fit profile. No implicit
behavioral tracking. This is a deliberate privacy choice — see
[evidence-and-references § 3.8](evidence-and-references.md).

## Privacy

### Where does my data go?

Nowhere. The prototype is local-only. The single network call is the
unauthenticated Open-Meteo weather lookup; everything else stays in
JSON files in the repo. See [Chapter 10](../book/10-privacy-security.md).

### Can I delete my data?

Yes — delete the JSON files. The product brief commits to encrypted,
opt-in, deletable data in any future production version. See
[Chapter 10](../book/10-privacy-security.md).

### Why does the privacy chapter cite GDPR if Wearly doesn't transmit data?

Because the *spirit* of GDPR (view, delete, export, object) is the
right design target even when the regulation doesn't technically apply.
Wearly's local-only stance is the strongest form of compliance: the data
never leaves the device. See
[evidence-and-references § 3.9](evidence-and-references.md).

## Knowledge graph

### What is the Wearly Knowledge Graph?

The [**Wearly Knowledge Graph**](sims/wearly-knowledge-graph/index.md)
is a three-layer structured-knowledge graph — **domain rules**,
**user-behavior aggregates**, and **runtime archetypes** — generated
deterministically by
[`scripts/generate_wearly_kg.py`](https://github.com/eatedalsf/styling-agent/blob/main/scripts/generate_wearly_kg.py)
into [`graph/wearly-knowledge-graph.json`](../graph/wearly-knowledge-graph.json).
91 nodes, 187 typed edges in the seed snapshot. It's the structured
context a future RAG or LLM shopping layer can query — every edge has
a typed `from` / `to` / `type`, and the citation chain is traversable
along graph hops.

### What does a bigger circle mean?

Aggregated user signal. An item you wear often grows; a color family
your closet keeps returning to grows; an occasion you attend often
grows. Domain archetypes (rule packs, weather bands, skin-tone palettes)
stay at base size so the user-behavior layer reads first.

### Where does the per-recommendation reasoning live?

Inside the app, as an expander below every outfit result — a numbered
reasoning trail that cites the specific rule (`<pack>#R<N>`) for each
decision. That's the live, per-run reasoning surface; the Wearly
Knowledge Graph is the structured-knowledge layer the runtime is
reasoning against.

## How this book works

### What does "Level 2 intelligent textbook" mean?

A term from [Dan McCreary's framework](https://dmccreary.github.io/intelligent-textbooks/).
A Level-2 book is built around a concept-dependency graph and ships
MicroSims, glossary, FAQ, references, and Bloom-tagged concepts.
Wearly is built to this level — see
[book/index.md](../book/index.md).

### Why are there MicroSims?

Because some concepts are easier to *play with* than to read about.
Color harmony and the freshness curve are good examples. Each sim is a
small self-contained p5.js or vis-network page under `docs/sims/`. See
[the sim index](sims/index.md).

### How do I cite Wearly?

The repo is at <https://github.com/eatedalsf/styling-agent>. A formal
metadata file lives at `book-metadata.yml` in the repo root. The
References page below lists the works the book itself draws on.

---

*Pattern follows `faq-generator` from
[dmccreary/claude-skills](https://github.com/dmccreary/claude-skills).
Answers stay short on purpose — each one points at a deeper chapter.*
