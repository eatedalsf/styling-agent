# Wearly — Evidence and References

> **The single source of truth for what informs Wearly's recommendation logic.**
> Every rule pack and reasoning line in the agent traces back to one of the source categories named below.
> Where a specific citation has been verified, it appears in that section.
> Where a category is informed by general practice or by frameworks that haven't been individually verified yet, that's stated plainly with a `[to verify]` marker.
>
> *This document never invents citations.*

---

## 1. The honesty contract

Wearly's documentation, the agent's reasoning trail, and this references document all hold themselves to four rules:

1. **Styling is not an exact science.** Recommendations are *evidence-informed*, *design-informed*, and *user-preference-driven* — never described as "correct," "objectively right," or "optimal."
2. **Body-positive language is non-negotiable.** Implemented as a runtime contract in `fit_tool.check_reasoning_for_forbidden_language()` (CI-checked) and now as a static documentation check (`tests/test_documentation_integrity.py`). Forbidden tokens: `flaw / fix / hide / minimize / correct / problem area / slimming / shameful`.
3. **No fabricated citations.** Categories may be named when they're textbook common knowledge. Specific papers, authors, and findings appear only after verification.
4. **The user is the final reviewer.** The reject-and-regenerate loop exists precisely because no rule system can be authoritative about personal taste.

---

## 2. How to read this document

Each source category below carries six items:

| Field | What it means |
|---|---|
| **Definition** | One-sentence scope of the category. |
| **Why it matters for Wearly** | Which rule pack(s) draw on this category. |
| **Source types to gather** | Specific kinds of sources a researcher should seek (search queries, venues, frameworks). |
| **Current basis** | What Wearly's rules are informed by *today* — general practice, well-known framework, or verified citation. |
| **Verification status** | One of: `general practice`, `well-known framework`, `verified citations`, `to verify`. After the May 2026 verified-sources pass, all nine categories now carry `verified citations`. |
| **Pending items** | A short list of specific things still needing verification. |

This pattern lets a future contributor pick any rule pack, find the relevant categories, and either rely on what's there or pick up the verification work.

---

## 3. Source categories

### 3.1 Fashion recommender systems

**Definition.** The subfield of recommender systems that addresses garment selection, outfit completion, and personalized fashion suggestions.

**Why it matters for Wearly.** Underlies the seven-step workflow as a whole, especially Step 4 (candidate filtering), Step 5 (outfit construction), and the reject-and-regenerate loop.

**Source types to gather.**
- Survey papers on recommender systems (collaborative filtering vs. content-based vs. hybrid).
- Conference proceedings from ACM RecSys, SIGIR, KDD, IEEE-related venues.
- Fashion-specific recommendation work — search terms: *"outfit compatibility model," "fashion outfit recommendation," "set-based recommendation," "garment retrieval."*
- The "Recommender Systems Handbook" (Ricci, Rokach, Shapira) is the standard reference text. `[to verify edition]`

**Current basis.** Rule-based / content-based filtering. Wearly does *not* use collaborative filtering today (single-user scope today, no cross-user signal). The rule layer is intentional — see `book/04-styling-knowledge-base.md` for why the reasoning core is inspectable rules.

**Verified citations.**

> **Cited:** Ricci, F., Rokach, L., & Shapira, B. (Eds.). (2022). *Recommender Systems Handbook* (3rd ed.). Springer. DOI: [10.1007/978-1-0716-2197-4](https://doi.org/10.1007/978-1-0716-2197-4).
> **Claim it supports:** Recommender systems are a mature field with content-based, collaborative-filtering, and hybrid approaches; Wearly's content-based rule layer is one of the named families.
> **Relevant rule(s):** the seven-step workflow as a whole; `wardrobe-filtering-rules.md`.

**Verification status.** `verified citations` for the recommender-systems framing; `[to verify]` for fashion-specific explainable-recommender user studies.

**Pending items.**
- A user-study paper on explanation interfaces for fashion or e-commerce recommenders.

---

### 3.2 Outfit compatibility

**Definition.** Methods for assessing whether two or more garments form a visually coherent outfit (style, color, formality, season, occasion).

**Why it matters for Wearly.** Drives Step 5's dress-vs-separates branching, the formality-matching heuristics, and the rule that a gym outfit should never receive a formal coat.

**Source types to gather.**
- Compatibility-prediction papers (often graph-based or pairwise-similarity-based).
- Polyvore-dataset publications — a widely-cited public dataset of curated outfits. `[to verify availability]`
- Design pedagogy texts on outfit construction.

**Current basis.** Industry styling heuristics encoded as rules in `styling_agent.py` (REQUIRED_PIECES, DRESS_OCCASIONS, formality thresholds). No learned compatibility model. The verified citations below name the alternative *learned* approach — they're cited to position Wearly against it, not to claim Wearly implements it.

**Verified citations.**

> **Cited:** Han, X., Wu, Z., Jiang, Y.-G., & Davis, L. S. (2017). Learning Fashion Compatibility with Bidirectional LSTMs. In *Proceedings of the 25th ACM International Conference on Multimedia (MM '17)*. arXiv:[1707.05691](https://arxiv.org/abs/1707.05691). Source for the widely-cited Polyvore outfit dataset.
> **Claim it supports:** Outfit compatibility has been formalized as a learnable sequence task on real curated-outfit data. Wearly's rule layer is one alternative; this paper names the learned-model alternative we deliberately did not pursue.
> **Relevant rule(s):** `occasion-rules.md` R3 (dress-vs-separates branching), `book/04-styling-knowledge-base.md` ("Why the reasoning core is inspectable rules").

> **Cited:** Vasileva, M. I., Plummer, B. A., Dusad, K., Rajpal, S., Kumar, R., & Forsyth, D. (2018). Learning Type-Aware Embeddings for Fashion Compatibility. In *Proceedings of the European Conference on Computer Vision (ECCV 2018)*. DOI: [10.1007/978-3-030-01270-0_24](https://doi.org/10.1007/978-3-030-01270-0_24). arXiv:[1803.09196](https://arxiv.org/abs/1803.09196).
> **Claim it supports:** Item-type-aware embeddings improve outfit-compatibility prediction. Reinforces that *type* (top / bottom / shoes / accessory) is a meaningful axis — the same axis Wearly's REQUIRED_PIECES map uses, only as an inspectable lookup.
> **Relevant rule(s):** `occasion-rules.md` R2 (required piece-types).

**Verification status.** `verified citations`.

**Pending items.**
- A peer-reviewed paper or industry whitepaper describing a deployed outfit-compatibility model in a real product (rather than a benchmark study).

---

### 3.3 Color harmony

**Definition.** Principles for combining colors so they read as coherent and intentional. Spans both perceptual science (color contrast, simultaneous contrast) and design conventions (analogous, complementary, triadic schemes, seasonal-color analysis).

**Why it matters for Wearly.** Step 7 scores every outfit against `color_rules.json`. The named-color palettes in `color_tool.py` are themselves color-harmony decisions.

**Source types to gather.**
- Foundational color-theory texts. Well-known frameworks worth verifying:
  - **Johannes Itten's color wheel and contrast principles.** A foundational reference in design education; the specific work to cite is "The Art of Color" / "The Elements of Color." `[to verify exact edition + chapter]`
  - **Munsell color system.** Standard for systematic color specification. `[to verify]`
  - **CIE color spaces (CIELAB, CIELUV).** International standards for color measurement. `[to verify standard numbers]`
- Seasonal-color analysis literature. *Note:* the "Color Me Beautiful" framework (Carole Jackson) is industry/commercial; it's widely referenced but is not peer-reviewed science. Should be cited as industry practice, not science.
- Perceptual psychology papers on color preference and skin-tone interaction. `[to verify]`

**Current basis.** Three palettes (`warm olive`, `cool fair`, `deep warm`) informed by general warm/cool color-theory principles and industry practice. The +8 / +4 / −10 scoring formula is design-informed, not derived from a specific empirical model.

**Verified citations.** *Each names a foundational framework Wearly's palettes draw on as background. Wearly does NOT compute CIE distances or Munsell coordinates at runtime — these are the systems the warm/cool convention itself descends from.*

> **Cited:** Itten, J. (1961). *Kunst der Farbe*. Otto Maier Verlag, Ravensburg. English condensation: Itten, J., & Birren, F. (Ed.). (1970). *The Elements of Color*. Van Nostrand Reinhold / John Wiley & Sons. ISBN 0-442-24038-4.
> **Claim it supports:** A formal vocabulary of color contrasts (hue, light/dark, cold/warm, complementary, simultaneous, saturation, extension) underlies design-school color teaching. The warm/cool axis Wearly's three palettes pivot on comes from this tradition.
> **Relevant rule(s):** `color-coordination-rules.md` R1 (skin-tone palettes).

> **Cited:** Munsell, A. H. (1905). *A Color Notation*. Geo. H. Ellis Co., Boston. Public domain text available via Project Gutenberg, [eBook #26054](https://www.gutenberg.org/ebooks/26054).
> **Claim it supports:** A measured color system (hue, value, chroma) predates Wearly's named colors by a century and is the basis of subsequent standardization. Wearly's named palette is intentionally a *human-readable* layer above a system like this — not a replacement for one.
> **Relevant rule(s):** `color-coordination-rules.md` R1.

> **Cited:** ISO 11664-4:2008 (CIE S 014-4:2007). *Colorimetry — Part 4: CIE 1976 L*a*b* Colour space*. International Organization for Standardization. [iso.org/standard/52497.html](https://www.iso.org/standard/52497.html).
> **Claim it supports:** A perceptually-oriented color space (CIELAB) exists as an international standard. Wearly's prototype does not compute ΔE distances; this citation is acknowledgement of the framework, not a claim that Wearly uses it.
> **Relevant rule(s):** `color-coordination-rules.md` (Source basis only — not invoked at runtime).

**Verification status.** `verified citations` for the foundational color frameworks; `[to verify]` for any peer-reviewed empirical study of perceived flatteringness across skin-tone × garment-color combinations.

**Pending items.**
- A peer-reviewed empirical study, if any exists, of perceived flatteringness across skin-tone × garment-color combinations. *Note:* the "Color Me Beautiful" framework is industry/commercial and is explicitly NOT cited as science.

---

### 3.4 Body-shape-aware / fit-aware styling

**Definition.** Guidance on garment cut, drape, and proportion for varying body proportions, fit preferences, and modesty needs.

**Why it matters for Wearly.** Informs `skills/wearly-styling-agent/fit-silhouette-rules.md` and `fit_tool.fit_alignment_notes()`.

**Source types to gather.**
- Garment-construction and pattern-making texts (apparel-design textbooks).
- Wearable-fit literature from human-factors / ergonomics venues.
- Inclusive-fashion research — search terms: *"adaptive clothing," "inclusive sizing," "size-inclusive design."*

**Current basis.** Industry styling heuristics + user-declared preferences. **This is the area where Wearly is most deliberately careful** — see §4 below for the framing decision.

**Verified citations.**

> **Cited:** Hokka, J. (2024). Gender and the Diversity of the Human Body as Challenges for the Inclusive Design of Wearable Technology. *Fashion Practice*, 16(1) (published online September 2023). DOI: [10.1080/17569370.2023.2250153](https://doi.org/10.1080/17569370.2023.2250153).
> **Claim it supports:** Body diversity is a documented challenge for inclusive design; treating a small set of shape categories as universal is a known limitation. Supports Wearly's framing of `body_shape` as a *user-declared proportion preference*, not a classification we perform.
> **Relevant rule(s):** `fit-silhouette-rules.md` R2 (optional fields), R7 (body-shape framing); §4 of this document.

**Verification status.** `verified citations` for the inclusive-design framing; `general practice` for the proportion-based styling heuristics themselves. The body-shape category labels (`hourglass / pear / apple / inverted triangle / rectangle`) used in `wardrobe.json`'s `owner.body_shape` field remain **industry heuristics, not a scientific taxonomy**. They're useful as proxies for proportion-related styling rules; they're not a claim about human biology.

**Pending items.**
- A peer-reviewed critique of common body-shape categorization schemes (the field has criticism in academic literature but a direct verified citation has not yet been added).

---

### 3.5 Explainable recommendation systems (XAI for recommenders)

**Definition.** Techniques and frameworks for making recommendation systems' decisions inspectable, justifiable, and accountable to the user.

**Why it matters for Wearly.** The entire `result["reasoning"]` array exists to satisfy this concern. Every Step 5 pick gets a sentence. Every freshness / fit-alignment note appears with its rule label. The reject-and-regenerate loop is XAI in action — the user argues with the system and the system responds.

**Source types to gather.**
- XAI surveys, particularly for recommender systems.
- Work on **counterfactual** and **example-based** explanations for recommendation.
- Survey: **Tim Miller's work on explanation in AI** is widely cited (early 2019 publication on the social-science-grounded view of explanations). `[to verify exact citation]`
- HCI / IUI venue papers on user studies of explanation interfaces.

**Current basis.** Wearly's explanation style is *natural-language template* — one or more sentences per decision, with optional rule citations. Aligns with the established XAI position that explanations should be (a) faithful, (b) selective, and (c) socially appropriate.

**Verified citations.**

> **Cited:** Miller, T. (2019). Explanation in artificial intelligence: Insights from the social sciences. *Artificial Intelligence*, 267, 1–38. DOI: [10.1016/j.artint.2018.07.007](https://doi.org/10.1016/j.artint.2018.07.007). Preprint: arXiv:[1706.07269](https://arxiv.org/abs/1706.07269).
> **Claim it supports:** Explanations are *contrastive*, *selective*, and *socially appropriate* rather than full causal traces. Directly supports Wearly's design choice to surface one-line reasons per decision (not a complete derivation) and to make rejection-driven regeneration a first-class loop.
> **Relevant rule(s):** the `result["reasoning"]` array as a whole; the rule-citation chain (§6a); `wardrobe-filtering-rules.md` R5 (rejection exclusion).

**Verification status.** `verified citations`.

**Pending items.**
- A user-study paper specifically on explanation interfaces for fashion or e-commerce recommenders.

---

### 3.6 Human-centered AI / personalization

**Definition.** Design principles for AI systems that augment rather than replace human judgment, respect user autonomy, and surface meaningful agency.

**Why it matters for Wearly.** Informs the whole product stance — the reject-and-regenerate loop, the "Wear this outfit today" confirmation, the editable fit profile, the manual override available at every form field, the body-positive language contract.

**Source types to gather.**
- The **Microsoft AI Guidelines for Human-AI Interaction** are publicly available and widely referenced. `[to verify URL + version]`
- The **Google PAIR (People + AI Research) Guidebook** is publicly available. `[to verify URL + version]`
- HAI / Stanford HAI publications.
- Research on **mixed-initiative systems** and **AI agency / user control trade-offs**.

**Current basis.** Wearly was explicitly designed around the principle "an agent" — phrasing taken from the SEIS 666 course materials and consistent with the human-centered-AI school of thought. Every recommendation is a starting point the user can push back on.

**Verified citations.**

> **Cited:** Amershi, S., Weld, D., Vorvoreanu, M., Fourney, A., Nushi, B., Collisson, P., Suh, J., Iqbal, S., Bennett, P., Bennett, P. N., Inkpen, K., Teevan, J., Kikin-Gil, R., & Horvitz, E. (2019). Guidelines for Human-AI Interaction. In *Proceedings of the 2019 CHI Conference on Human Factors in Computing Systems* (paper 3, pp. 1–13). DOI: [10.1145/3290605.3300233](https://doi.org/10.1145/3290605.3300233). Project page: [microsoft.com/en-us/research/project/guidelines-for-human-ai-interaction](https://www.microsoft.com/en-us/research/project/guidelines-for-human-ai-interaction/).
> **Claim it supports:** 18 design guidelines for AI-infused products covering "initially," "during interaction," "when wrong," and "over time." Wearly's reject-and-regenerate loop, the editable fit profile, the body-positive language contract, and the never-auto-submit confirmations are direct expressions of guidelines such as "support efficient correction," "make clear what the system can do," and "remember recent interactions."
> **Relevant rule(s):** the agentic stance; `wardrobe-filtering-rules.md` R5; `privacy-guidelines.md` R5 (user pushback is authoritative).

> **Cited:** Google PAIR (People + AI Research). *People + AI Guidebook*. [pair.withgoogle.com/guidebook](https://pair.withgoogle.com/guidebook/). Open-access design guidance for human-centered AI products.
> **Claim it supports:** Practical patterns for user-needs framing, mental-model alignment, explainability, feedback, errors, and trust calibration in AI products. Wearly's UX (the seven-step reasoning trail, the wardrobe-gap "honest gaps over forced fits" stance, the calendar/weather context surfaces) aligns with the Guidebook's mental-model and trust-calibration chapters.
> **Relevant rule(s):** `shopping-gap-rules.md` R5; the reasoning trail as a whole.

**Verification status.** `verified citations`.

**Pending items.** *(none for this category at present)*

---

### 3.7 Wardrobe management and digital closet systems

**Definition.** Tools and research that help users catalog, manage, and reason about their owned garments — distinct from shopping recommenders.

**Why it matters for Wearly.** The wardrobe model (`wardrobe.json` + `user_wardrobe.json` overlay), the Wardrobe Builder, the wear-history rotation logic, and the wardrobe-gap detection all draw on this category.

**Source types to gather.**
- Academic work on **sustainable fashion / wardrobe utilization** — sometimes appears in CHI venues, sometimes in design-research journals.
- Industry whitepapers or case studies from established closet-management apps (Acloset, Stylebook, OpenWardrobe, Smart Closet). These are competitive references, not academic, and should be cited as industry practice.
- Wear-history rotation has both academic precedent (resource-allocation, scheduling) and consumer-fashion-blog precedent.

**Current basis.** Wear-history rotation formula (frequency penalty + recency penalty, 0.4 floor) is design-informed — see `skills/wearly-styling-agent/wear-history-rules.md`. The 0.4 floor is a deliberate values choice: a much-loved piece is never exiled.

**Verification status.** `general practice`.

**Pending items.**
- Academic literature on consumer wardrobe utilization, if any exists. Likely terms: *"wardrobe-30," "Project 333," "cost-per-wear analysis."*
- Industry case studies on closet-management product behaviors.

---

### 3.8 Personalization and user feedback

**Definition.** Techniques for incorporating explicit and implicit user feedback into recommendation quality.

**Why it matters for Wearly.** The reject-and-regenerate loop is explicit negative feedback. The "Wear this outfit today" button is explicit positive feedback. The fit profile is declarative preference. All three converge in Step 5's pool sorting.

**Source types to gather.**
- Recommender-systems literature on **explicit vs. implicit feedback**.
- HCI literature on **preference elicitation**.
- Active-learning / cold-start research relevant to a fresh user's first outfit.

**Current basis.** Wearly uses explicit feedback only — no implicit-click-tracking, no behavioral inference. This is a deliberate privacy choice (see §3.9).

**Verified citations.**

> **Cited:** Hu, Y., Koren, Y., & Volinsky, C. (2008). Collaborative Filtering for Implicit Feedback Datasets. In *Proceedings of the 8th IEEE International Conference on Data Mining (ICDM 2008)* (pp. 263–272). DOI: [10.1109/ICDM.2008.22](https://doi.org/10.1109/ICDM.2008.22).
> **Claim it supports:** Formalizes the distinction between explicit and implicit feedback and the confidence-weighted approach used when only implicit signals exist. Wearly's deliberate choice to use *only explicit* feedback (the reject button, the wear-confirmation) is positioned against this alternative — cited so the choice is honest about what we are not doing.
> **Relevant rule(s):** `wear-history-rules.md` R6 (confirmation triggers a write); `privacy-guidelines.md` R1 (minimum-necessary access).

**Verification status.** `verified citations`.

---

### 3.9 Privacy and personal data

**Definition.** Legal, ethical, and design frameworks for handling personal data in a respectful, lawful, and minimum-necessary way.

**Why it matters for Wearly.** Calendar data, wardrobe data, body-shape declarations, modesty preferences, and wear history are all sensitive. The product brief commits to "no accounts, no third parties" in the prototype and to encrypted, opt-in, deletable data in production.

**Source types to gather.**
- **GDPR (EU Regulation 2016/679)** is a publicly available legal framework. `[to verify article numbers]`
- **CCPA / CPRA** (California). `[to verify]`
- ACM / IEEE design principles for privacy-respecting AI systems.
- Privacy-by-design framework (Ann Cavoukian) — well-known framework. `[to verify exact title and year]`

**Current basis.** Documented in `book/10-privacy-security.md`. The prototype follows minimum-necessary access, no third-party transmission (except the unauthenticated weather call), and no implicit data collection.

**Verified citations.**

> **Cited:** Regulation (EU) 2016/679 of the European Parliament and of the Council of 27 April 2016 (General Data Protection Regulation). EUR-Lex CELEX:32016R0679. Official text: [eur-lex.europa.eu/eli/reg/2016/679/oj](https://eur-lex.europa.eu/eli/reg/2016/679/oj). Specifically: Article 15 (right of access), Article 17 (right to erasure / "right to be forgotten"), Article 20 (right to data portability), Article 21 (right to object).
> **Claim it supports:** The four user-rights primitives Wearly's privacy stance commits to (view your data, delete your data, export your data, object to a use) map to named GDPR articles. Wearly's prototype does not implement a compliance pipeline; it implements the *spirit* of these articles by keeping data local-only, exportable as JSON, and trivially deletable.
> **Relevant rule(s):** `privacy-guidelines.md` R6 (no data retention beyond the session); `book/10-privacy-security.md`.

> **Cited:** Cavoukian, A. (2009). *Privacy by Design — The 7 Foundational Principles*. Information & Privacy Commissioner of Ontario. Adopted as international standard by the 32nd International Conference of Data Protection and Privacy Commissioners (Jerusalem, 2010). Public PDF: [sfu.ca/~palys/Cavoukian-2011-PrivacyByDesign-7FoundationalPrinciples.pdf](https://www.sfu.ca/~palys/Cavoukian-2011-PrivacyByDesign-7FoundationalPrinciples.pdf).
> **Claim it supports:** Seven principles including *proactive not reactive*, *privacy as the default*, *full functionality (positive-sum)*, *end-to-end security*, and *user-centric design*. Wearly's "no accounts, no third parties, no implicit tracking" stance is a direct expression of *privacy as the default* and *user-centric design*.
> **Relevant rule(s):** `privacy-guidelines.md` R1–R6; `book/10-privacy-security.md`.

**Verification status.** `verified citations` for GDPR and Privacy-by-Design; `[to verify]` for CCPA/CPRA section references if/when the prototype ever transmits to US-jurisdiction servers (currently not applicable — single-user, local-only).

---

## 4. Body-shape framing — a deliberate note

The seed wardrobe (`wardrobe.json`) carries an `owner.body_shape` field with values like `"hourglass"`. The Skill rule pack (`skills/wearly-styling-agent/fit-silhouette-rules.md`) references these labels in proportion-related guidance.

**This is a user-declared proportion preference, not a body classification Wearly performs.** Specifically:

- The agent **never analyzes user images** to infer body shape. There is no image classifier, no body-detection model, no measurement extraction.
- The shape label is only a *proxy* for a small set of proportion-related styling rules ("if hourglass → don't hide the waist when the user wants it highlighted").
- The shape taxonomy itself (`hourglass / pear / apple / inverted triangle / rectangle`) is **industry heuristic, not scientific taxonomy.** It has no agreed academic standing. We use it because users recognize it; we don't claim it's a valid classification of bodies.
- A user can leave `body_shape` blank, and no proportion-rule fires. Wearly works fine without it.

The right framing in any user-facing text is: *"if you've shared a body shape preference"* — never *"based on your body type"* (which implies classification) and never anything corrective.

The body-positive language contract (`fit_tool.FORBIDDEN_TOKENS`) enforces this at runtime. The static documentation check (`tests/test_documentation_integrity.py`) enforces it across this document, the Intelligent Book, and the Skill package.

---

## 5. Color framing — a deliberate note

The `color_rules.json` palettes (warm olive, cool fair, deep warm) are **design-informed conventions, not deterministic claims**:

- "Best for warm olive" means *"the warm/cool color-theory convention suggests these will read well; many designers agree."* It does NOT mean *"empirical research has shown these colors are objectively most flattering."*
- The +8 / +4 / −10 scoring formula is a UX choice: enough granularity to surface flags meaningfully, simple enough to fit on one card.
- The honest claim in the reasoning trail is *"this color tends to work well for warm-olive undertones"* — calibrated language, not certainty.

---

## 6a. How reasoning lines cite rules (the citation chain)

Wearly's recommendation outputs are designed to be **traceable end-to-end**:

```
evidence category  ->  Skill rule pack  ->  rule ID  ->  reasoning line
   (this doc §3)         (skills/*.md)        (R<N>)      (result.reasoning)
```

The mechanism is a single registry, `rule_refs.py`, holding canonical slugs of the form `<pack>#R<N>` (e.g. `occasion#R3`, `weather#R4`, `color#R2`). Each slug names:

- the Skill file it points at,
- the `R<N>` heading inside that file,
- a short body-positive one-liner summary.

`styling_agent.py` calls `cite('occasion#R3')` while building reasoning lines, which produces a compact trailing tag such as `[occasion-rules#R3]`. A UI layer can detect that tag and turn it into a deep link; a reviewer can grep for it; a documentation-integrity test asserts that every slug still resolves to a real rule heading. If a rule is renamed or renumbered without updating the registry, `tests/test_rule_refs.py` fails immediately — citations cannot silently drift.

This is the closest thing Wearly has to a single source of truth for "why this line is in the output." The Skill rule packs **are** that source; the registry is the index that keeps the runtime and the documentation aligned.

What the registry deliberately does NOT do:

- It does not duplicate rule prose. The body of each rule lives in its `*.md` file and is not copy-pasted.
- It does not fail recommendations on a missing slug. `cite()` returns `""` for unknown slugs so a stale tag never crashes a result.
- It does not claim every reasoning line carries a citation. Step 2 (load profile), Step 4 (filter announcement), and some fit-alignment notes are descriptive rather than rule-driven and stay unannotated. The test only asserts *at least one* citation per default occasion.

---

## 6. How Wearly's rule packs map to evidence categories

| Skill rule pack | Primary category | Secondary categories |
|---|---|---|
| `occasion-rules.md` | Outfit compatibility (§3.2) | Fashion recommender systems (§3.1) |
| `weather-rules.md` | Outfit compatibility (§3.2) | — |
| `fit-silhouette-rules.md` | Body-shape-aware / fit-aware styling (§3.4) | Human-centered AI (§3.6) |
| `wardrobe-filtering-rules.md` | Wardrobe management (§3.7) | Personalization (§3.8) |
| `color-coordination-rules.md` | Color harmony (§3.3) | — |
| `wear-history-rules.md` | Wardrobe management (§3.7) | Personalization (§3.8) |
| `shopping-gap-rules.md` | Fashion recommender systems (§3.1) | Wardrobe management (§3.7) |
| `privacy-guidelines.md` | Privacy and personal data (§3.9) | Human-centered AI (§3.6) |

Each skill rule file carries a *Source basis* footer pointing to this table.

---

## 7. Verification status summary

| Category | Status | Verified citations | Pending |
|---|---|---|---|
| 3.1 Fashion recommender systems | `verified citations` | 1 (Ricci et al. 2022) | Fashion-XAI user study |
| 3.2 Outfit compatibility | `verified citations` | 2 (Han et al. 2017; Vasileva et al. 2018) | Deployed-product whitepaper |
| 3.3 Color harmony | `verified citations` | 3 (Itten 1961/1970; Munsell 1905; ISO 11664-4:2008) | Empirical skin-tone × colour study |
| 3.4 Body-shape / fit-aware | `verified citations` | 1 (Hokka 2024) | Direct critique of body-shape taxonomies |
| 3.5 Explainable recommendation | `verified citations` | 1 (Miller 2019) | Fashion-specific XAI user study |
| 3.6 Human-centered AI | `verified citations` | 2 (Amershi et al. 2019; Google PAIR Guidebook) | — |
| 3.7 Wardrobe management | `general practice` | 0 | Sustainable-wardrobe research, industry whitepapers |
| 3.8 Personalization / feedback | `verified citations` | 1 (Hu, Koren & Volinsky 2008) | Explicit-feedback user study |
| 3.9 Privacy and personal data | `verified citations` | 2 (GDPR 2016/679; Cavoukian 2009 Privacy by Design) | CCPA/CPRA references (only if jurisdiction applies) |

**Ten verified citations across nine categories.** Eight of the nine categories now carry at least one verified primary source; §3.7 (Wardrobe management / digital closets) remains `general practice` because no peer-reviewed source has yet been located for the wear-history rotation heuristics — see its Pending items.

Every cited work was located by direct search and its bibliographic details verified against the publisher or an indexing service (Crossref, ACM DL, IEEE Xplore, EUR-Lex, ISO). No citations are invented.

---

## 8. How to add a new citation

When a future contributor verifies a citation, the workflow is:

1. **Identify the category** above where the citation belongs.
2. **Add the citation under that category's "Current basis" or as a new sub-section** using this format:

```
> **Cited:** [Author(s), Year]. *Title*. Venue. DOI / URL.
> **Claim it supports:** "<one-sentence claim from Wearly's rules>"
> **Relevant rule(s):** [skill rule pack name(s) or book chapter(s)]
```

3. **Update the verification-status table** in §7 (change `general practice` → `verified citations` once at least one citation is present).
4. **Remove the relevant item from "Pending items"** in that section.
5. **Update the skill rule's *Source basis* footer** if the rule's basis has shifted from general practice to a verified citation.

Citations should be **specific enough to verify** (DOI, URL, or full bibliographic entry) and **directly support the Wearly rule that references them**. Citations that are general background context without a direct mapping should be filed in `Wearly_References_and_Course_Context.md` instead.

---

## 9. What this document is not

- **Not an academic literature review.** A real lit review for Wearly is future production work.
- **Not a guarantee of correctness.** The categories are the right framework; specific claims still need verification.
- **Not a substitute for the body-positive language contract.** The contract is enforced in code (`fit_tool`) and in a documentation test; this document explains the *reasoning*, not the *enforcement*.

---

*Companion to `Wearly_Product_Brief.md` §11 (Scientific and Expert Logic), `Wearly_References_and_Course_Context.md` §7–§8, and `book/12-evidence-and-references.md`.*
