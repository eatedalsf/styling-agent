# Wearly AI — 10-Minute Demo Script

> **Skeleton.** Fill in concrete copy and timings as later phases ship.
> **Target audience:** SEIS 666 instructor and class.
> **Goal:** Show a working, reasoning agent — not a chatbot or slide deck.

---

## At a glance

| # | Section | Target time |
|---|---|---|
| 1 | Opening hook / problem | 0:45 |
| 2 | What Wearly AI is | 0:45 |
| 3 | Before / After demo | 1:15 |
| 4 | Calendar + weather reasoning | 1:15 |
| 5 | Wardrobe + color reasoning | 1:15 |
| 6 | Error handling & wardrobe gaps | 0:45 |
| 7 | Knowledge graph + Intelligent Book | 1:15 |
| 8 | Future product roadmap | 1:00 |
| 9 | Closing | 0:30 |
| | **Total** | **~10:00** |

---

## 1. Opening hook / problem (0:45)

**Goal:** Make the audience feel the problem in 45 seconds.

- Open with a relatable scene: busy morning, calendar full, weather uncertain, closet overwhelming.
- One pain statistic or quote ("the average person spends ~15 minutes deciding what to wear, often without checking weather or calendar").
- One sentence: *"What if your closet could reason about your day for you?"*

> *TBD: final opening copy.*

---

## 2. What Wearly AI is (0:45)

**Goal:** Position Wearly AI as an **agent**, not a chatbot.

- Mobile-first, clean-luxury personal styling agent.
- For busy women now; men, children, and family workflows later.
- Reasons through: **calendar · weather · location · wardrobe · fit profile · wear history · favorite stores**.
- Built with structured context and visible reasoning — not random prompting.

> *TBD: branded one-slide visual.*

---

## 3. Before / After demo (1:30)

**Goal:** Make the workflow delta unmistakable.

- **Before** — generic chatbot suggestion: vague outfit, no context, no weather, no reasoning.
- **After** — Wearly AI: pulls calendar event, fetches live weather, filters wardrobe, applies color rules, returns a complete outfit with explanation.
- Run command: `python main.py --compare` *(or the Streamlit "Before / After Demo" mode)*.

> *TBD: side-by-side screenshot or recording.*

---

## 4. Calendar + weather reasoning (1:30)

**Goal:** Show how external context shapes the recommendation.

- Open Wearly AI, point to the upcoming event ("Team Strategy Meeting · 2026-05-12 · 10:00 AM").
- Show the live weather card (Minneapolis temperature, condition, layering advice).
- Highlight the reasoning line that connects them: e.g. *"Added Camel Wool Coat as outerwear — temperature is 57.8°F and a light jacket or trench coat is recommended."*
- One sentence: *"This is not a guess. This is the agent reading your calendar and the sky."*

> *TBD: screenshot of the occasion + weather cards.*

---

## 5. Wardrobe + color reasoning (1:30)

**Goal:** Show personalization beyond context.

- Walk through the **outfit card** — every piece named, every color chip visible.
- Open the **color harmony score** — explain the 0–100 scoring tied to the user's skin tone.
- Open the **reasoning expander** — show 6–8 numbered decisions including color notes.
- One sentence: *"Every item is here for a reason. The agent explains itself."*

> *TBD: screenshot of the outfit + color score + reasoning panel.*

---

## 6. Error handling & wardrobe gaps (1:00)

**Goal:** Show graceful degradation — the rubric line item.

- Demo path: run `python main.py --everyday "gym"` *(or pick gym in Streamlit)*.
- Point out that **no occasion-appropriate outerwear exists** in the wardrobe.
- Show the gap card: *"Missing: outerwear → A lightweight athletic windbreaker or running jacket would cover cool-weather gym transit without breaking the activewear look."*
- One sentence: *"A chatbot would fake an answer. Wearly AI says what's missing — and what to buy."*

> *TBD: screenshot of the gap alert.*

---

## 7. Knowledge graph + Intelligent Book (1:15)

**Goal:** Show that Wearly isn't a black box — it's a model you can read.

- Still on the outfit result screen, scroll to *"Reasoning graph — how this outfit emerged."* Expand it.
- **The graph appears.** Walk through it: *"User → CalendarEvent → Weather → these five WardrobeItems → Outfit. Drag a node. Hover the Outfit diamond — you see every piece. This is the same logic the agent just ran, in graph form."*
- If you've done reject-and-regenerate earlier in the demo, point at the **Feedback nodes** with the `excludes_from_pool` edges — that's the user's pushback, made visible.
- Jump to the **Before / After** tab, scroll to the bottom: *"View the schema graph."* Expand it. *"This is the abstract model — 9 entity types, 14 relation types. Every recommendation traces through this graph."*
- One more pivot: *"And we documented all of it."* Open <https://eatedalsf.github.io/styling-agent/> in a new tab. Show:
  - The Intelligent Book chapters (12 of them).
  - The Evidence-and-references doc with the nine source categories.
  - The Skill rule packs with their *Source basis* footers.
  - The body-positive language contract.
- One sentence: *"Wearly says 'tends to work well,' not 'is correct.' Every rule traces to a source category. Nothing is fabricated."*

> *Visual: split your screen — the running app on the left showing the live-run graph, the docs site on the right showing the chapter on agent workflow. The graph in the app and the schema in the book are the same model, one concrete and one abstract.*

---

## 8. Future product roadmap (1:00)

**Goal:** Show this is an MVP with a credible path forward.

Walk briefly through the roadmap from `Wearly_Product_Brief.md` §13:

- **Now**: working agent with calendar, weather, wardrobe, color reasoning.
- **Next**: mobile-first UI, fit/body profile, wear history, reject/regenerate.
- **Then**: shopping with favorite stores, wishlist, Intelligent Book, Knowledge Graph, Skills.
- **Production**: real Google Calendar, Apple Calendar, native iOS app, family profiles, image processing.

**Privacy note:** Calendar, weather/location, wardrobe, and profile data are used **only** for outfit planning in this prototype.

> *TBD: roadmap visual.*

---

## 9. Closing (0:30)

**Goal:** Land the message in one sentence.

- One-line recap: *"Wearly AI turns a closet into a context-aware agent."*
- Point to the GitHub repo and the `Wearly_Product_Brief.md`.
- Invite questions.

> *TBD: final closing slide.*

---

## Run sheet (presenter cheat sheet)

| Step | Command / action |
|---|---|
| Pre-demo | `pip install -r requirements.txt` *(once)* |
| Pre-demo | Open the live app (or `streamlit run app.py`) in a browser tab; resize to mobile width for the first half of the demo |
| Pre-demo | Open <https://eatedalsf.github.io/styling-agent/> in a second tab, ready for §7 |
| §3 | Open **Before / After** in the app sidebar; tap **See it live →** |
| §4–§5 | Tap **Home → Plan today's outfit →** (or `python main.py`) |
| §6 | Sidebar → **Everyday Occasion → Gym** → **Plan this occasion** |
| §7 | On the outfit screen, expand **"Reasoning graph — how this outfit emerged."** Drag a node. Then **Before / After → View the schema graph**. Then switch to the docs-site tab. |

**Encoding note for Windows:** if the CLI shows `UnicodeEncodeError`, set `PYTHONIOENCODING=utf-8` once per shell session — but the latest `main.py` already auto-reconfigures UTF-8, so this should not be needed.

---

*This script is a living skeleton — refine copy, timings, and visuals as later phases ship.*
