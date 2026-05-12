# SEIS 666 Track B — Self-evaluation

> Mapped against the Spring 2026 project description. Cited where verified; honest where pending.

---

## Track B deliverables — line-by-line

| Track B requirement | Wearly's evidence | Status |
|---|---|---|
| Working agent built with Claude Code / API / framework | Built with Claude Code (Claude Opus 4.7). Live Streamlit Cloud + CLI. | **Exceeded** |
| ≥ 2 external tools | **4 external + 5 internal tools** (calendar, weather API, wardrobe, color; fit, history, shopping, graph, backup). | **2× minimum** |
| Documented decision tree / process flow | 7 named steps + `workflow_diagram.md` (Mermaid) + interactive in-app pyvis graph + in-book vis-network.js viewer + Learning Graph DAG. | **Exceeded** |
| Error handling for unexpected input | Weather fallback, empty-pool relaxation, rejection loop, atomic JSON writes, body-positive contract refusal path. Every tool has a documented fallback. | **Met** |
| Before/after comparison | CLI `python main.py --compare` + UI **Before/After Demo** screen + quantified delta table (see §3 of `demo_script.md`). | **Exceeded** |
| 10-min presentation | `demo_script.md` with full timing, pre-baked Q&A, run sheet. | **Met** |

---

## Section 5 rubric — projected scoring

| Criteria | Weight | Wearly's evidence |
|---|---|---|
| Working System | 30% | Live Streamlit Cloud + CLI + **207 passing tests** + 4 external tools |
| Domain Depth | 20% | 12-chapter Intelligent Book + 8 Skill rule packs + 9 evidence categories + **10 verified primary citations** + body-positive contract |
| Before/After Delta | 20% | Quantified table (15 min → 30 sec; 0 → 7-12 reasoning lines; 0 → 10 citations) |
| Documentation | 15% | MkDocs site, README, architecture, schemas, demo script, citation chain, business-model doc |
| Presentation | 15% | Pending May 14 — rehearse against `demo_script.md` |

---

## Section 2 "Best Practices" alignment

| # | Principle | Wearly |
|---|---|---|
| 1 | Structure beats prompts | ✅✅✅ Skill rule packs + KG + Learning Graph + Evidence chain |
| 2 | Show the delta | ✅ Two surfaces (CLI flag + UI screen) + numeric table |
| 3 | Pick a domain you know | ✅ Personal styling — relatable, no jargon |
| 4 | Build, don't theorize | ✅ Live app + live book — no PowerPoint hypotheticals |
| 5 | Use AI to build the project | ✅ Built with Claude Code, documented |
| 6 | Who would pay for this | ✅ `docs/business-model.md` — three buyers identified |
| 7 | Audit trail matters | ✅✅✅ `rule_refs.py` registry + `cite()` + reasoning-line tags |
| 8 | Start small, go deep | ✅ 7 well-scoped steps, deep on each |

---

## Why Wearly is an agent (and not a chatbot)

| Property | Chatbot | True Agent | Wearly |
|---|---|---|---|
| Workflow has named steps in defined order | ❌ | ✅ | ✅ 7 steps |
| Uses external tools | usually ❌ | ✅ | ✅ live weather API + 3 others |
| Branches on tool data | ❌ | ✅ | ✅ dress vs separates, gym branching, outerwear injection, gap detection |
| Pursues a goal beyond responding | ❌ | ✅ | ✅ complete appropriate outfit |
| Recovers from unexpected input | ❌ | ✅ | ✅ documented fallback per tool |
| Closed feedback loop | ❌ | ✅ | ✅ reject + regenerate |
| Persistent memory across sessions | ❌ | ✅ | ✅ `wear_history.json` |
| Outputs traceable to structured rules | ❌ | ✅ | ✅ `[occasion-rules#R3]` tags |
| Multi-tool orchestration in one task | ❌ | ✅ | ✅ 4 tools per recommendation |

**Verdict:** Unambiguous. Wearly satisfies every hallmark of an agent.

---

## How Wearly compares to the "What Great Projects Look Like" examples (Section 6)

| Their A-grade example | Wearly's parallel |
|---|---|
| Legal Discovery Agent: graph traversal + reasoning paths | Wearly KG + citation chain — every reasoning line points to a graph entity + a numbered rule |
| Supply Chain Risk Graph: cascade analysis | Wearly's User → Event → Recommendation → Items → Gap → Suggestion cascade |
| Code Review Agent: read input + check against rules + write review | Wearly: read calendar/weather + check against 8 rule packs + write reasoned outfit |
| Healthcare Billing Optimizer: codes + payer rules + audit trail | Wearly: occasion + season + fit + color + history + audit trail with verified citations |
| Real Estate Analyzer: scrape + analyze + memo | Wearly: pull context + run 7 steps + produce reasoning trail + shopping memo |

Wearly maps cleanly onto every example. The audit-trail-with-citations layer goes beyond what any single example specifies.

---

## What Wearly delivers *beyond* the Track B baseline

Track B did not require any of the following — Wearly delivers each anyway:

- Track-A-level Knowledge Graph (9 entity types, formal schema, interactive viewers in both app and book).
- Intelligent Textbook — 12 chapters + 28-concept Learning Graph with Bloom taxonomy + p5.js micro-sim.
- Agent Skill package conforming to **agentskills.io** Advanced tier (YAML frontmatter + executable validator).
- **Citation chain end-to-end** (evidence → rule pack → rule ID → reasoning line), tested.
- **10 verified primary citations** (Springer, ACM, IEEE, ECCV, ISO, EUR-Lex).
- Body-positive language contract enforced twice (runtime + docs).
- Compact-KG export per outfit (instructor's "save the session as a compact KG" idea, delivered).
- "Today's context" free-text input (Leah's life-context pattern, applied).
- "Ask your wardrobe" pre-baked queries (Leah's KG-traversal pattern, applied).
- Auto-deployed GitHub Pages site with GH Actions.

---

## Honest pending items

- **Demo rehearsal** — `demo_script.md` is now complete but unrehearsed. Practice runs recommended.
- **Wardrobe-management research citation** (Evidence §3.7) — still `general practice`; no peer-reviewed source for wear-history rotation has been located.
- **CCPA/CPRA references** (Evidence §3.9) — only relevant if jurisdiction expands.
- **Fashion-specific XAI user study** — still pending across §3.1 and §3.5.

---

## Repo + live links

- **GitHub repo**: <https://github.com/eatedalsf/styling-agent>
- **Live app**: <https://styling-agent-64jigzmqms4v7f9ugou8bv.streamlit.app/>
- **Intelligent Book**: <https://eatedalsf.github.io/styling-agent/>
