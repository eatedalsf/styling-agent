# References

> A flat, numbered bibliography of every work Wearly's Intelligent Book
> draws on. The references support the Skill rules, and the Skill
> rules are what the styling-agent prototype applies at runtime — so
> this page is the deepest layer of the citation chain:
> **reference → evidence category → rule pack → reasoning line in the
> app.** Sources are listed in the order they appear in
> [evidence-and-references.md](evidence-and-references.md). Each entry
> includes the section it supports and the rule pack(s) it informs.
>
> Pattern follows the Level-2 framework at
> [dmccreary/intelligent-textbooks](https://dmccreary.github.io/intelligent-textbooks/) —
> a flat numbered list is what reviewers, instructors, and other
> textbooks tend to cite back to.

---

## How to read this page

- Citations are numbered **[1]** through **[10]**.
- Each entry shows: *Author(s) (Year). Title. Venue. DOI / URL.*
- The **Supports** line names the Wearly chapter, evidence section, or
  rule pack the citation directly backs.
- The longer narrative with each citation's *Claim it supports* sentence
  lives in [evidence-and-references.md](evidence-and-references.md);
  this page is the scannable index version.

---

## Bibliography

**[1]** Ricci, F., Rokach, L., & Shapira, B. (Eds.). (2022).
*Recommender Systems Handbook* (3rd ed.). Springer.
DOI: [10.1007/978-1-0716-2197-4](https://doi.org/10.1007/978-1-0716-2197-4).

- *Supports*: [evidence § 3.1 Fashion recommender systems](evidence-and-references.md);
  seven-step workflow framing.
- *Rule packs*: [`wardrobe-filtering-rules.md`](../skills/wearly-styling-agent/wardrobe-filtering-rules.md).

**[2]** Han, X., Wu, Z., Jiang, Y.-G., & Davis, L. S. (2017).
Learning Fashion Compatibility with Bidirectional LSTMs. In *Proceedings
of the 25th ACM International Conference on Multimedia (MM '17)*.
arXiv:[1707.05691](https://arxiv.org/abs/1707.05691).

- *Supports*: [evidence § 3.2 Outfit compatibility](evidence-and-references.md);
  the "Why the reasoning core is inspectable rules" stance.
- *Rule packs*: [`occasion-rules.md`](../skills/wearly-styling-agent/occasion-rules.md) (R3, dress-vs-separates).

**[3]** Vasileva, M. I., Plummer, B. A., Dusad, K., Rajpal, S., Kumar, R.,
& Forsyth, D. (2018). Learning Type-Aware Embeddings for Fashion
Compatibility. In *Proceedings of the European Conference on Computer
Vision (ECCV 2018)*.
DOI: [10.1007/978-3-030-01270-0_24](https://doi.org/10.1007/978-3-030-01270-0_24).
arXiv:[1803.09196](https://arxiv.org/abs/1803.09196).

- *Supports*: [evidence § 3.2 Outfit compatibility](evidence-and-references.md);
  the type-aware framing of REQUIRED_PIECES.
- *Rule packs*: [`occasion-rules.md`](../skills/wearly-styling-agent/occasion-rules.md) (R2, required piece-types).

**[4]** Itten, J. (1961). *Kunst der Farbe*. Otto Maier Verlag, Ravensburg.
English condensation: Itten, J., & Birren, F. (Ed.). (1970).
*The Elements of Color*. Van Nostrand Reinhold / John Wiley & Sons.
ISBN 0-442-24038-4.

- *Supports*: [evidence § 3.3 Color harmony](evidence-and-references.md);
  the warm/cool axis the three palettes pivot on.
- *Rule packs*: [`color-coordination-rules.md`](../skills/wearly-styling-agent/color-coordination-rules.md) (R1, skin-tone palettes).

**[5]** Munsell, A. H. (1905). *A Color Notation*. Geo. H. Ellis Co., Boston.
Public domain via [Project Gutenberg eBook #26054](https://www.gutenberg.org/ebooks/26054).

- *Supports*: [evidence § 3.3 Color harmony](evidence-and-references.md);
  framing the named palette as a human-readable layer above a measured
  system.
- *Rule packs*: [`color-coordination-rules.md`](../skills/wearly-styling-agent/color-coordination-rules.md) (R1).

**[6]** ISO 11664-4:2008 (CIE S 014-4:2007). *Colorimetry — Part 4: CIE
1976 L\*a\*b\* Colour space*. International Organization for Standardization.
[iso.org/standard/52497.html](https://www.iso.org/standard/52497.html).

- *Supports*: [evidence § 3.3 Color harmony](evidence-and-references.md);
  acknowledgement of perceptual color spaces (Wearly does not compute
  ΔE — this is named for honesty about what we don't do).
- *Rule packs*: [`color-coordination-rules.md`](../skills/wearly-styling-agent/color-coordination-rules.md) (source basis only).

**[7]** Hokka, J. (2024). Gender and the Diversity of the Human Body as
Challenges for the Inclusive Design of Wearable Technology.
*Fashion Practice*, 16(1).
DOI: [10.1080/17569370.2023.2250153](https://doi.org/10.1080/17569370.2023.2250153).

- *Supports*: [evidence § 3.4 Body-shape / fit-aware styling](evidence-and-references.md);
  the framing of `body_shape` as a user-declared preference, not a
  classification.
- *Rule packs*: [`fit-silhouette-rules.md`](../skills/wearly-styling-agent/fit-silhouette-rules.md) (R2 optional fields, R7 body-shape framing).

**[8]** Miller, T. (2019). Explanation in artificial intelligence:
Insights from the social sciences. *Artificial Intelligence*, 267, 1–38.
DOI: [10.1016/j.artint.2018.07.007](https://doi.org/10.1016/j.artint.2018.07.007).
Preprint: arXiv:[1706.07269](https://arxiv.org/abs/1706.07269).

- *Supports*: [evidence § 3.5 Explainable recommendation](evidence-and-references.md);
  the design choice of contrastive, selective, socially appropriate
  one-line explanations.
- *Rule packs*: the `result["reasoning"]` array;
  [`wardrobe-filtering-rules.md`](../skills/wearly-styling-agent/wardrobe-filtering-rules.md) R5 (rejection exclusion).

**[9]** Amershi, S., Weld, D., Vorvoreanu, M., Fourney, A., Nushi, B.,
Collisson, P., Suh, J., Iqbal, S., Bennett, P., Bennett, P. N., Inkpen, K.,
Teevan, J., Kikin-Gil, R., & Horvitz, E. (2019). Guidelines for Human-AI
Interaction. In *Proceedings of the 2019 CHI Conference on Human Factors
in Computing Systems* (paper 3, pp. 1–13).
DOI: [10.1145/3290605.3300233](https://doi.org/10.1145/3290605.3300233).
Project page:
[microsoft.com/en-us/research/project/guidelines-for-human-ai-interaction](https://www.microsoft.com/en-us/research/project/guidelines-for-human-ai-interaction/).

- *Supports*: [evidence § 3.6 Human-centered AI](evidence-and-references.md);
  the agentic stance and the reject-and-regenerate loop.
- *Rule packs*: [`wardrobe-filtering-rules.md`](../skills/wearly-styling-agent/wardrobe-filtering-rules.md) R5; [`privacy-guidelines.md`](../skills/wearly-styling-agent/privacy-guidelines.md) R5.

**[10]** Google PAIR (People + AI Research). *People + AI Guidebook*.
[pair.withgoogle.com/guidebook](https://pair.withgoogle.com/guidebook/).

- *Supports*: [evidence § 3.6 Human-centered AI](evidence-and-references.md);
  mental-model and trust-calibration framing.
- *Rule packs*: [`shopping-gap-rules.md`](../skills/wearly-styling-agent/shopping-gap-rules.md) R5; the reasoning trail as a whole.

**[11]** Hu, Y., Koren, Y., & Volinsky, C. (2008). Collaborative Filtering
for Implicit Feedback Datasets. In *Proceedings of the 8th IEEE
International Conference on Data Mining (ICDM 2008)* (pp. 263–272).
DOI: [10.1109/ICDM.2008.22](https://doi.org/10.1109/ICDM.2008.22).

- *Supports*: [evidence § 3.8 Personalization and user feedback](evidence-and-references.md);
  the explicit/implicit feedback distinction (Wearly uses *only* explicit).
- *Rule packs*: [`wear-history-rules.md`](../skills/wearly-styling-agent/wear-history-rules.md) R6; [`privacy-guidelines.md`](../skills/wearly-styling-agent/privacy-guidelines.md) R1.

**[12]** Regulation (EU) 2016/679 of the European Parliament and of the
Council of 27 April 2016 (General Data Protection Regulation).
EUR-Lex CELEX:32016R0679.
Official text: [eur-lex.europa.eu/eli/reg/2016/679/oj](https://eur-lex.europa.eu/eli/reg/2016/679/oj).
Cited articles: 15 (right of access), 17 (right to erasure), 20 (right to
data portability), 21 (right to object).

- *Supports*: [evidence § 3.9 Privacy and personal data](evidence-and-references.md);
  the four user-rights primitives.
- *Rule packs*: [`privacy-guidelines.md`](../skills/wearly-styling-agent/privacy-guidelines.md) R6; [Chapter 10](../book/10-privacy-security.md).

**[13]** Cavoukian, A. (2009). *Privacy by Design — The 7 Foundational
Principles*. Information & Privacy Commissioner of Ontario. Adopted as
international standard by the 32nd International Conference of Data
Protection and Privacy Commissioners (Jerusalem, 2010).
PDF: [sfu.ca/~palys/Cavoukian-2011-PrivacyByDesign-7FoundationalPrinciples.pdf](https://www.sfu.ca/~palys/Cavoukian-2011-PrivacyByDesign-7FoundationalPrinciples.pdf).

- *Supports*: [evidence § 3.9 Privacy and personal data](evidence-and-references.md);
  the "no accounts, no third parties, no implicit tracking" stance.
- *Rule packs*: [`privacy-guidelines.md`](../skills/wearly-styling-agent/privacy-guidelines.md) R1–R6; [Chapter 10](../book/10-privacy-security.md).

---

## Source-of-truth notes

- This page is **derived** from [evidence-and-references.md](evidence-and-references.md).
  When a citation is added or updated, edit the evidence document first
  (where the per-citation *Claim it supports* lives), then mirror the
  bibliographic entry here.
- The numbering is stable per release — citations are never renumbered
  retroactively. New citations are appended.
- A pending verification still listed in
  [evidence-and-references.md § Pending items](evidence-and-references.md)
  does *not* appear here. Only verified entries land in the
  bibliography.

---

## Frameworks referenced (not formally cited)

These are named in the book and the Intelligent Book pattern itself, but
are not Wearly-rule citations. They're included as a reading list for
contributors.

- McCreary, D. *Intelligent Textbooks Framework*. <https://dmccreary.github.io/intelligent-textbooks/>.
  The Level-2 pattern this book is built to.
- McCreary, D. *Claude Skills*. <https://github.com/dmccreary/claude-skills>.
  The generator-skill patterns (glossary, FAQ, references, learning graph)
  the book mirrors.
- McCreary, D. *Graph LMS*. <https://github.com/dmccreary/graph-lms>.
  The graph-rendering pattern the learning-graph viewer extends.

---

*This page is the scannable index version of the citations.
[evidence-and-references.md](evidence-and-references.md) is the canonical
narrative version with verification status, pending items, and the rule-pack
mapping table.*
