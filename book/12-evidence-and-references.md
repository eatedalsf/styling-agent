# 12 · Evidence and references

*The app applies rules; this chapter explains the evidence base those rules trace back to and what still needs verification.*

Wearly's recommendation logic is **evidence-informed, design-informed, and user-preference-driven** — never described as exact or objectively correct. This chapter explains *what* informs the agent's reasoning and *how* the project handles the gap between "general practice" and "verified citations."

The canonical, structured version of this material lives in [`docs/evidence-and-references.md`](../docs/evidence-and-references.md). This chapter is the readable summary.

---

## The honesty contract

Four rules govern every claim Wearly makes:

1. **Styling is not an exact science.** Wearly says "tends to work well," not "is correct."
2. **Body-positive language is non-negotiable.** Enforced at runtime by `fit_tool.check_reasoning_for_forbidden_language()` and across documentation by `tests/test_documentation_integrity.py`. Forbidden tokens: `flaw, fix, hide, minimize, correct, problem area, slimming, shameful`.
3. **No fabricated citations.** Categories are named when they're textbook common knowledge; specific authors, papers, and findings appear only after verification.
4. **The user is the final reviewer.** Reject-and-regenerate, the editable fit profile, and the "Wear this outfit" confirmation all exist because no rule system can be authoritative about personal taste.

---

## The nine source categories

Every rule pack in `skills/wearly-styling-agent/` and every reasoning line in the agent traces back to one or more of these:

| # | Category | What it informs |
|---|---|---|
| 1 | Fashion recommender systems | The seven-step workflow as a whole |
| 2 | Outfit compatibility | Step 5 dress-vs-separates branching, formality matching |
| 3 | Color harmony | Step 7 color scoring, `color_rules.json` palettes |
| 4 | Body-shape-aware / fit-aware styling | Step 5 fit-alignment notes, `fit-silhouette-rules.md` |
| 5 | Explainable recommendation systems | The entire `result["reasoning"]` array |
| 6 | Human-centered AI / personalization | The "agent, not a chatbot" stance, reject-and-regenerate |
| 7 | Wardrobe management / digital closets | Wardrobe builder, wear-history rotation, gap detection |
| 8 | Personalization and user feedback | Explicit feedback loops (reject, mark-worn, edit profile) |
| 9 | Privacy and personal data | Minimum-necessary data handling, no third parties |

The full table in `docs/evidence-and-references.md` §6 maps each skill rule pack to its primary and secondary categories.

---

## Where Wearly is most careful

### Body shape

The seed wardrobe carries `owner.body_shape: "hourglass"`. This is **a user-declared proportion preference, not a body classification Wearly performs.** The agent never analyzes images to infer shape; it only respects the label the user gave it as a proxy for proportion-related styling rules.

The shape taxonomy itself (`hourglass / pear / apple / etc.`) is **industry heuristic, not scientific taxonomy.** It has no agreed academic standing. Wearly uses it because users recognize it — not as a claim about human biology.

### Color palettes

The `color_rules.json` palettes are **design-informed conventions, not deterministic claims.** "Best for warm olive" means *"warm/cool color-theory convention suggests these will read well."* It does not claim empirical proof. The +8 / +4 / −10 scoring formula is a UX choice for readability, not a derived empirical model.

### Recommender model class

Wearly uses **content-based, rule-driven recommendation** — not collaborative filtering (which would require cross-user signals we don't collect for privacy reasons) and not deep-learned outfit compatibility (which would be unexplainable). This is documented in §3.1 of the references doc.

---

## The citation chain — runtime to rule pack

Reasoning lines aren't just prose. Where the agent acted on a Skill rule, the line ends with a compact tag such as `[occasion-rules#R3]` or `[weather#R4]`. Those tags are sourced from a single registry, `rule_refs.py`, that maps each slug to:

- the Skill file it points at (`skills/wearly-styling-agent/*.md`),
- the `R<N>` heading inside that file,
- a one-line body-positive summary.

A documentation-integrity test (`tests/test_rule_refs.py`) asserts that every registered slug resolves to a real rule heading and that the agent's default-occasion runs always emit at least one citation. If a rule is renumbered without updating the registry, the test fails — citations cannot silently drift.

This closes the chain **evidence category → rule pack → rule ID → reasoning line**. The Skill rule packs *are* the source of truth; `rule_refs.py` is the index that keeps the runtime aligned with them. See `docs/evidence-and-references.md` §6a for the longer explanation.

---

## Verification status

After a verified-sources pass, **ten primary citations have been added** across eight of the nine source categories. Each was located by direct search and its bibliographic details verified against the publisher or an indexing service (Crossref, ACM Digital Library, IEEE Xplore, EUR-Lex, ISO). No citations are invented.

Highlights:

- **Recommender systems:** Ricci, Rokach & Shapira (Eds.), *Recommender Systems Handbook*, 3rd ed., Springer 2022.
- **Outfit compatibility:** Han et al. 2017 (Polyvore dataset, ACM MM); Vasileva et al. 2018 (type-aware embeddings, ECCV).
- **Color frameworks:** Itten 1961 (*The Art of Color*); Munsell 1905 (*A Color Notation*); ISO 11664-4:2008 (CIELAB).
- **Inclusive design:** Hokka 2024 (*Fashion Practice*).
- **Explainable AI:** Miller 2019 (*Artificial Intelligence* 267).
- **Human-centered AI:** Amershi et al. 2019 (CHI, Microsoft's 18 guidelines); Google PAIR *People + AI Guidebook*.
- **Implicit-vs-explicit feedback:** Hu, Koren & Volinsky 2008 (ICDM).
- **Privacy:** GDPR Regulation (EU) 2016/679 (Articles 15, 17, 20, 21); Cavoukian 2009 *Privacy by Design — The 7 Foundational Principles*.

§3.7 (Wardrobe management / digital closets) remains `general practice` — no peer-reviewed source has yet been located for the wear-history rotation heuristics. The full per-category status table lives in `docs/evidence-and-references.md` §7.

Honest framing: citations name the *frameworks Wearly's rules draw on*. They do not claim Wearly has implemented those frameworks' algorithms (e.g., Wearly does not compute CIE ΔE distances). Where a citation names an *alternative* approach Wearly deliberately did not take (e.g., learned outfit-compatibility models, implicit-feedback collaborative filtering), the citation is included so the design choice is honest about what was considered and rejected.

---

## What this chapter is not

- **Not an academic literature review.** That's future production work.
- **Not a guarantee of correctness.** The framework is solid; specific claims need verification.
- **Not a substitute for the body-positive language contract.** The contract is enforced by code and tests; this chapter explains the principles behind it.

---

## Where to verify

- **Canonical references list:** `docs/evidence-and-references.md`.
- **Body-positive language contract (code):** `fit_tool.check_reasoning_for_forbidden_language()`.
- **Body-positive language contract (docs):** `tests/test_documentation_integrity.py`.
- **Course philosophy:** `Wearly_References_and_Course_Context.md` §3 and §7.
- **Per-rule source mapping:** the *Source basis* footer of each file in `skills/wearly-styling-agent/`.

---

## Key terms

- **Evidence categories** — the nine source categories every Wearly rule traces back to ([glossary](../docs/glossary.md)).
- **Citation chip** — the `[pack#R<N>]` tag — the runtime side of the citation chain ([glossary](../docs/glossary.md)).
- **Honesty contract** — no fabricated citations; categories named only when textbook-common ([glossary](../docs/glossary.md)).

## Self-check

1. *(Remember)* How many evidence categories does Wearly organize its sources under?
2. *(Understand)* Why is the *Color Me Beautiful* framework deliberately *not* cited as science in §3.3?
3. *(Apply)* Pick any reasoning line from a recent agent run. Trace its citation chip back to an evidence category.

*Definitions live in the [Glossary](../docs/glossary.md). Self-check questions follow Bloom's taxonomy progression (Remember → Understand → Apply → Analyze) — the same tags used in the [Learning Graph](../docs/sims/learning-graph/index.md).*
