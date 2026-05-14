# S8 · Body-positive framing as a discipline

*Part II teaches the styling knowledge the prototype reasons over; this chapter explains the language contract that runs across every other rule and why the discipline is enforced in code, not only in documentation.*

## The concept

Most popular styling literature is written in **corrective**
vocabulary — *flaw, fix, hide, minimize, slimming, problem area,
flatter, shameful*. The words frame styling as a project of *changing
the wearer* to fit an external ideal. Wearly explicitly refuses that
framing.

The replacement is **body-positive framing as a discipline.** Two
sentences capture the rule:

1. Wearly **honors** what the wearer has shared about their
   preferences. It never describes a feature of the wearer as
   something to correct.
2. Wearly's vocabulary is **calibrated** — *"tends to work well,"*
   *"a clean line,"* *"a balanced look"* — never deterministic
   judgments like *"is most flattering"* or *"hides this."*

The discipline is enforced at two levels.

### Level 1 — runtime forbidden tokens

The function `fit_tool.check_reasoning_for_forbidden_language()`
inspects every reasoning line the agent emits and refuses any line
that contains a forbidden token. The list today:

```
flaw, fix, hide, minimize, correct, problem area, slimming, shameful
```

A reasoning line that trips the check fails CI; a developer cannot
ship copy that violates the contract without removing it from this
list deliberately. The list grows when a reviewer surfaces a token
that should be banned and the team agrees.

### Level 2 — static documentation check

`tests/test_documentation_integrity.py` walks every Markdown file in
the book, the Skill pack, and the references doc and asserts none of
the forbidden tokens appears. The discipline is not just for the
runtime output; the *documentation about the agent* holds itself to
the same standard.

If a contributor writes *"hides the waist"* in a chapter, the test
suite fails. Body-positive framing is not a stylistic preference; it
is a structural property of the project.

## Why this is a methodology, not a style choice

A style choice would be a recommendation in a contributor guide.
Wearly's body-positive framing is structural for three reasons:

1. **The audience is mostly women.** The corrective vocabulary in
   styling literature does identifiable harm; the SEIS 666 project's
   evidence-informed framing requires that the project not perpetuate
   it.
2. **The contract is testable.** A vocabulary rule that *can* fail
   CI is one a future contributor cannot quietly drop. The
   `FORBIDDEN_TOKENS` set is a contract surface.
3. **The framing affects the rule design, not just the copy.**
   Because the agent can't say *"hides the waist,"* it has to find a
   different framing — *"this silhouette honors the wearer's preferred
   waist definition."* That different framing requires a different
   rule shape (preference-aware, not correction-aware), which
   ultimately is a different agent.

## Edge cases and their resolutions

- **"Balance"** is allowed; **"correct"** is not. Balance is a
  styling vocabulary about composition; correction is about the
  wearer.
- **"Highlight"** is allowed and encouraged. Highlighting a feature
  the wearer has *chosen* to share is body-positive; the choice came
  from the user.
- **Numbers (sizes, measurements)** are never used as judgment. A
  measurement in the fit profile is a coordinate, not a rating; the
  rule pack documents this explicitly.
- **"Recommendation"** carries no judgment by itself; the agent
  *recommends* outfits. The rejected verbs are the ones that
  describe the wearer rather than the garment.

## Where this knowledge comes from

- **Hokka (2024)** documents body diversity as a known challenge for
  inclusive design and frames small-set categorization as a
  limitation rather than a truth. Wearly's framing — every body-shape
  field optional, body-shape labels as user-declared preferences —
  is the direct expression of that framing.
  ⟶ [References [7]](../docs/references.md).
- **Miller (2019)** on explanations in AI argues that explanations
  should be *contrastive, selective, and socially appropriate.*
  Body-positive framing is the *socially appropriate* axis applied to
  styling reasoning lines.
  ⟶ [References [8]](../docs/references.md).
- **Amershi et al. (2019)** on Human-AI Interaction guidelines
  includes *"Match relevant social norms"* and *"Mitigate social
  biases."* Wearly's forbidden-token contract is one operational
  expression of both.
  ⟶ [References [9]](../docs/references.md).

## How Wearly applies this

| Where | What happens |
|---|---|
| **Rule pack** | [`fit-silhouette-rules.md`](../skills/wearly-styling-agent/fit-silhouette-rules.md) — R1 (body-positive contract) |
| **Runtime code** | `fit_tool.FORBIDDEN_TOKENS`, `fit_tool.check_reasoning_for_forbidden_language()` |
| **Static check** | `tests/test_documentation_integrity.py` |
| **Where it surfaces** | Implicitly in every reasoning line; explicitly in [Chapter 06](06-fit-profile-logic.md) and [Chapter 12](12-evidence-and-references.md) |
| **Part I chapter** | [Chapter 06 · Fit-profile logic](06-fit-profile-logic.md) |
| **MicroSim** | *(none — this rule is cross-cutting, not a single-rule sim)* |

---

## Key terms

- **Body-positive language contract** — the runtime + documentation rule that forbids corrective vocabulary. See [Glossary](../docs/glossary.md).
- **Honesty contract** — the four rules that govern every claim Wearly makes; body-positive language is one of them. See [Glossary](../docs/glossary.md).
- **Forbidden tokens** — the eight tokens (`flaw, fix, hide, minimize, correct, problem area, slimming, shameful`) that fail CI.

## Self-check

1. *(Remember)* List four forbidden tokens from the body-positive language contract.
2. *(Understand)* Why is body-positive framing called a *discipline* rather than a *style choice*?
3. *(Apply)* You're writing a new reasoning line. You want to say *"this dress hides the waist."* Rewrite it so it passes the contract and means something coherent.
