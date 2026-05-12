# 12 · Evidence and references

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

Today, **zero citations have been individually verified.** Every section in `docs/evidence-and-references.md` currently relies on:

- General practice (industry styling heuristics and design conventions).
- Well-known frameworks (Itten color theory, GDPR, privacy-by-design, Microsoft AI Guidelines).

The references document lists 14 specific pending verification items — concrete searches a future contributor can complete. When a citation is verified, it gets added to the appropriate category, the verification-status table updates, and the relevant Skill rule's *Source basis* footer gets a citation link.

This is honest framing for a prototype: the *categories* are right, the *specific support* still needs work.

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
