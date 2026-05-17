# Screenshot shot list — 6 must-capture moments

Six screenshots, ~5 minutes total. These work either as additions to
the deck (slot them in as new slides between 6 and 7) or as standalone
LinkedIn carousel images alongside the deck.

**Save each to `press-kit/screenshots/` using the filename listed.**

Use the **Windows Snipping Tool** (`Win + Shift + S`) for app
screenshots, and the **browser's full-page screenshot** (`Ctrl+Shift+I`
→ device toolbar → "Capture full size screenshot") for the book + graph.

---

## 1️⃣ `01-home.png` — App Home (the agent stance)

**Where**: Live app → click **Home** in the top nav.

**Capture**: Above the fold. Should show the wordmark, the "An agent,
not a chatbot" headline, and the four "How Wearly thinks" pills (or
whatever the current Home composition is).

**Suggested caption** (if used standalone):

> The Wearly home screen. Context-first stance, seven-step reasoning
> loop, every decision cited.

---

## 2️⃣ `02-today-reasoning.png` — A real outfit with the reasoning trail open

**Where**: Live app → **Today** → click **Plan today's outfit →** →
scroll to the recommendation → expand **"How Wearly reasoned through this"**.

**Capture**: The outfit cards above plus the expanded reasoning trail
below. The reasoning trail should show numbered steps with rule
citations like `[color-coordination-rules#R2]`.

**Suggested caption**:

> Every recommendation prints a numbered reasoning trail that cites a
> named rule for every decision. Auditable by design.

---

## 3️⃣ `03-knowledge-graph.png` — The Knowledge Graph page

**Where**: Live app → click your name top-right → **Knowledge Graph**.

**Capture**: The full page including the "Knowledge Graph" header,
the "What size means" expander, and the embedded viewer with the
gray-to-black gradient + pastel nodes visible.

**Suggested caption**:

> The Wearly Knowledge Graph — your closet as a structured-knowledge
> system. 91 nodes, 187 typed edges, three layers.

---

## 4️⃣ `04-book-home.png` — Intelligent Book home

**Where**: https://eatedalsf.github.io/styling-agent/

**Capture**: Above the fold. Should show the wordmark and the
introduction. Left sidebar nav should be visible — proves the book
has chapters + the Wearly Knowledge Graph.

**Suggested caption**:

> The Intelligent Book — a Level-2 textbook companion to the running
> app (per Dan McCreary's framework). 11 chapters in Part I, 8 styling
> rule references in Part II, plus the Knowledge Graph.

---

## 5️⃣ `05-book-knowledge-graph.png` — The book's Knowledge Graph chapter

**Where**: Book → **Wearly Knowledge Graph → Structured knowledge (interactive)**.

**Capture**: Full-page screenshot or above-the-fold showing the chapter
heading + the embedded graph viewer with nodes visible. The
gray-to-black gradient should be visible.

**Suggested caption**:

> Click any node for details, double-click to highlight its 1-hop
> neighborhood. The same viewer is embedded inside the app, and
> queryable by any future RAG or LLM layer.

---

## 6️⃣ `06-wardrobe-view.png` — Wardrobe page (showing items + the knowledge-graph mini-view)

**Where**: Live app → **Wardrobe** tab → scroll to the bottom.

**Capture**: Show several wardrobe items at the top + the **"Your
wardrobe at a glance"** embedded mini Knowledge Graph at the bottom.
This is the clearest proof that the agent's structured knowledge
travels with the user, not just with the demo.

**Suggested caption**:

> The Wardrobe page ends with a live "Your wardrobe at a glance" mini
> Knowledge Graph — the same graph the book renders, populated from
> the user's real wardrobe + wear history when they click *Regenerate
> from my data*.

---

## Optional bonus shots (if you want to make a longer LinkedIn carousel)

| File | What | Where |
|---|---|---|
| `07-skill-package.png` | The Claude Skill spec | Open `skills/wearly-styling-agent/SKILL.md` on GitHub |
| `08-test-suite.png` | Tests passing | Terminal showing `Ran 393 tests in X.XXXs / OK` |
| `09-rule-pack.png` | A rule pack with rule numbering | Open `skills/wearly-styling-agent/color-coordination-rules.md` on GitHub |

---

## Where to put them in the deck

The current deck doesn't have screenshots — it's clean and concept-led.
If you'd like to insert them, the cleanest places are:

- **After slide 3** ("An agent, not a chatbot") → insert `01-home.png` and
  `02-today-reasoning.png` as proof of the claim.
- **After slide 7** ("The Wearly Knowledge Graph") → insert
  `03-knowledge-graph.png` and `05-book-knowledge-graph.png` as proof of the claim.
- **After slide 6** ("The Intelligent Book") → insert `04-book-home.png`.

To add a screenshot slide to the PPTX:

1. Open the PPTX in PowerPoint.
2. Right-click the slide you want to insert AFTER in the slide panel → **New Slide → Blank Layout**.
3. Drag the image onto the slide.
4. Resize to fill, leave a thin white border, add a small caption text box at the bottom.

Or rebuild the deck — `build_deck.js` already has all the layout
helpers; adding a screenshot slide is ~10 lines.
