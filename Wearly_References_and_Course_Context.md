# Wearly AI References and Course Context

> Companion document to `Wearly_Product_Brief.md`.
> Organizes the course context, instructor expectations, and research/reference strategy for Wearly AI.

---

## 1. SEIS 666 Project Context

Wearly AI is being developed for:

- **SEIS 666** — Digital Transformation with AI
- **Final Project** — Build Something That Reasons
- **Track** — Track B: Agentic AI System

The project must demonstrate:

- a working system,
- a multi-step workflow,
- at least two tools or data sources,
- a documented decision process,
- error handling,
- a before/after comparison,
- GitHub documentation, and
- a 10-minute demo.

**The final deliverable should be a working product prototype** — not only a PDF, slide deck, or concept explanation. The app is the product; documents support it.

---

## 2. Official Course and Project References

- **SEIS 666 Project Description**
  <https://yarmoluk.github.io/Digital-Transformation-with-AI-Spring-2026/class/SEIS666-Project-Description-Spring2026.pdf>

- **SEIS 666 Course Site**
  <https://yarmoluk.github.io/Digital-Transformation-with-AI-Spring-2026/>

- **SEIS 666 Course Bible**
  <https://yarmoluk.github.io/Digital-Transformation-with-AI-Spring-2026/class/SEIS666-Course-Bible-Spring2026.pdf>

- **Class Notes**
  <https://yarmoluk.github.io/class-note/>

---

## 3. Course Principles Relevant to Wearly AI

The following course principles directly shape Wearly AI's design philosophy:

- **Build, do not only theorize.** A working artifact is the deliverable.
- **Context is the product.** Quality of recommendations comes from organized context — calendar, weather, wardrobe, fit, history — not from clever prompts alone.
- **Structure beats volume.** Well-structured small data and rules outperform large, unstructured input.
- **AI systems should reason with organized context, not random prompting.** The reasoning trace must be visible and defensible.
- **The strongest projects show how AI changes the workflow before and after.** A clear delta between manual and agent-assisted styling is required.
- **The final app remains the main product.** Documentation, books, and graphs support the app; they do not replace it.

---

## 4. Intelligent Book References

The **Intelligent Book is not the product itself.** It is a structured documentation and reasoning layer that supports the working app.

The Intelligent Book for Wearly AI should explain:

- product vision,
- user problem,
- agent workflow,
- styling knowledge base,
- wardrobe intelligence,
- fit / body profile logic,
- calendar and weather context,
- shopping gap logic,
- before/after demo,
- privacy and security, and
- product roadmap.

### References

- **Intelligent Textbooks**
  <https://dmccreary.github.io/intelligent-textbooks/>

- **Intelligent Textbooks (GitHub)**
  <https://github.com/dmccreary/intelligent-textbooks>

---

## 5. Agent Skills and Meta-Skills References

The Skills folder should package **reusable workflows, rules, decision logic, references, and validation checks** for the Wearly Styling Agent.

The Wearly skill should eventually include:

- `SKILL.md`,
- occasion rules,
- weather rules,
- fit and silhouette rules,
- wardrobe filtering rules,
- color coordination rules,
- wear history rules,
- shopping gap rules, and
- privacy guidelines.

### References

- **Agent Skills**
  <https://agentskills.io/home>

- **Meta-Skills**
  <https://dmccreary.github.io/prompt-class/lectures/meta-skills/>

---

## 6. Lessons from Class Demo Feedback

Synthesized from prior class project feedback:

- The instructor prefers a **working MVP**, not just a PDF or slide deck.
- The demo should show the system working **live**.
- The project should clearly show **why it is an agent, not a chatbot**.
- The project should have a **clear target audience**.
- The project should include a **strong before/after comparison**.
- The project should explain the **decision process**, not only show the final output.
- The project should address **privacy and security** when using personal data such as calendar, location, wardrobe photos, measurements, preferences, and shopping behavior.
- The project should mention **testing or UAT**, even if full UAT is future work.
- The strongest projects feel like **real products or serious prototypes**, not toy examples.

---

## 7. Research Strategy for Styling Logic

Wearly AI's recommendation logic should be **evidence-informed**, not based only on generic prompting.

It should combine:

- fashion recommendation system research,
- color harmony principles,
- body-positive fit and silhouette rules,
- occasion and formality rules,
- weather and location constraints,
- wardrobe availability,
- wear history,
- user rejection reasons, and
- user feedback.

> Styling is not an exact science. Wearly AI should combine evidence-informed rules, user preferences, context, and feedback — rather than claim there is one universally correct outfit.

---

## 8. Academic and Expert References

The canonical, structured references document is **[`docs/evidence-and-references.md`](docs/evidence-and-references.md)** — see also Intelligent Book chapter [`book/12-evidence-and-references.md`](book/12-evidence-and-references.md). Nine source categories, mapped to each Skill rule pack, with a verification-status table.

### Source categories Wearly draws on

| # | Category | Status |
|---|---|---|
| 1 | Fashion recommender systems | General practice |
| 2 | Outfit compatibility | General practice |
| 3 | Color harmony | General practice (warm/cool framework, Itten / Munsell / CIE pending verification) |
| 4 | Body-shape-aware / fit-aware styling | General practice (industry heuristic, not scientific taxonomy) |
| 5 | Explainable recommendation systems | General practice (Miller 2019 pending verification) |
| 6 | Human-centered AI / personalization | Well-known framework (Microsoft AI Guidelines, Google PAIR pending verification) |
| 7 | Wardrobe management / digital closets | General practice |
| 8 | Personalization and user feedback | General practice |
| 9 | Privacy and personal data | Well-known framework (GDPR, privacy-by-design pending verification) |

### Honesty contract

- **No fabricated citations.** Categories are named when they're textbook common knowledge; specific authors, papers, and findings appear only after verification.
- **Body-shape category labels are industry heuristic, not scientific taxonomy** — Wearly never claims a user "is" a body shape; the label is a user-declared proportion preference.
- **Color palettes are design-informed conventions, not deterministic claims** — the language is *"tends to read well,"* not *"is correct."*
- **Body-positive language is enforced** at runtime in code and statically across documentation.

### 14 pending verification items

Concrete searches a future contributor can complete — full list in `docs/evidence-and-references.md` §7. Highlights:

1. Recommender Systems Handbook (Ricci, Rokach, Shapira) — edition.
2. Polyvore-dataset paper or successor (outfit-compatibility benchmark).
3. Itten color wheel — verified publisher / edition.
4. Munsell color system — verified standard reference.
5. CIE color spaces — CIELAB / CIELUV standard numbers.
6. Tim Miller, "Explanation in Artificial Intelligence" — verified citation.
7. Microsoft AI Guidelines for Human-AI Interaction (18 guidelines) — URL + version.
8. Google PAIR Guidebook — URL + current version.
9. GDPR — specific article numbers for user-rights claims in `book/10-privacy-security.md`.
10. Ann Cavoukian privacy-by-design framework — title + year.
11. Peer-reviewed study (if any) of skin-tone × garment-color preference.
12. Peer-reviewed work on body-shape taxonomy validity (or counter-perspectives).
13. Inclusive-fashion / fat-positive design research.
14. A fashion-XAI user study (HCI / IUI venue).

When a citation is verified, the workflow is in `docs/evidence-and-references.md` §8.

---

## 9. How These References Should Be Used

| Reference set | Role in Wearly AI |
|---|---|
| **SEIS 666 project references** | Define what the project must demonstrate (rubric, deliverables, tracks). |
| **Course references** | Define the philosophy — reasoning, context, structure, and working systems. |
| **Intelligent Book references** | Guide the documentation structure that supports the app. |
| **Agent Skills references** | Guide the reusable skill package layout and content. |
| **Styling research references** | Guide the recommendation logic so it is evidence-informed, not generic. |

**The final app must remain the main product.** References, documents, books, and graphs support the product — they do not replace the working demo.

---

## 10. Immediate Next Step

After this file and `Wearly_Product_Brief.md` are created, the next step is to:

1. Ask Claude Code to **read both files**,
2. **Review the current repository**, and
3. **Create a phased master implementation plan** — without immediately editing code.

The implementation plan should align with the roadmap in `Wearly_Product_Brief.md` (Phase 0 → Phase 6) and respect the principles, references, and instructor expectations summarized here.

---

*Companion to `Wearly_Product_Brief.md`. Together these two documents form the foundation for the Wearly AI build.*
