# 11 · Product roadmap

*The app is the prototype state; this chapter explains where the agent goes next and why each phase is ordered the way it is.*

Where Wearly is going. Mirrors the roadmap in `Wearly_Product_Brief.md` §13 but explains each phase in product-engineering terms.

## Status today

| Phase | Title | State |
|---|---|---|
| 0 | Foundation reliability | ✅ Shipped |
| 1 | Rebrand + demo polish | ✅ Shipped |
| 2 | Mobile-first UI shell + product screens | ✅ Shipped |
| 4 (partial) | Reject & regenerate | ✅ Shipped |
| 6 | Intelligent Book + Knowledge Graph + Agent Skill package | 🟡 In progress (this book is part of it) |
| 7 (partial) | Smoke tests + architecture doc | ✅ Shipped |
| 3 | Data model split + fit profile wiring | Not started |
| 4 (remaining) | Wardrobe builder + wear history rotation | Not started |
| 5 | Shopping + wishlist + favorite stores | Not started |
| 7 (remaining) | CI + final demo polish | In progress |

## Near-term (before final demo)

### Deploy and capture hero

- **Push** the branch to GitHub.
- **Deploy** to Streamlit Community Cloud (one click after push).
- **Capture** a 60–90 second screen GIF of the full flow: home → tap CTA → outfit + reasoning → reject an item → regenerate → "what changed" banner.
- **Update** the README hero block with the live URL and the embedded GIF.

### First chapter of Intelligent Book ✅

Done in this batch — chapters 01 through 11 of this book, plus the knowledge graph and skill package.

### CI workflow

GitHub Actions running `python -m unittest discover tests` on every push. A green badge in the README.

## Medium-term (after final demo)

### Phase 3 — Data model split

Move `owner` out of `wardrobe.json` into:

- `data/user_profile.json` — name, locale, city, privacy preferences.
- `data/fit_profile.json` — all the optional measurement and preference fields.

Add `fit_tool.py` to wire the fit profile into Step 5 of the agent.

### Phase 4 (remaining) — Wardrobe builder

- Add-by-photo screen with a Streamlit file uploader.
- White-background composite (prototype simulation; real `rembg` behind an optional install).
- Add-by-URL flow with manual field confirmation (real per-store scraping is future production).
- Edit / delete on any wardrobe item.
- `data/wear_history.json` driving rotation.
- Per-item reject popovers on the outfit card (the multiselect form ships in Phase 2; per-item is a polish pass).

### Phase 5 — Shopping & wishlist

- `data/stores.json` — favorite stores.
- `data/wishlist.json` — saved suggestions.
- `shopping_tool.suggest(gap, stores)` returning store-prioritized cards.
- Wishlist screen.

## Long-term (production)

### Native mobile app

Streamlit is the prototype surface. Real users will live in a native iOS app (Swift / SwiftUI) with the agent running server-side. The Streamlit prototype's API contract becomes the server's API contract.

### Real integrations

- Google Calendar (OAuth).
- Apple Calendar (CalDAV or native iOS Calendar permission).
- Geolocation (opt-in, coarse).
- Affiliate-compliant shopping catalogs.

### Family workflows

- Parent-managed child profiles.
- Coordinated family outfits ("dress us alike for the family photo").
- School uniform support.
- Stricter privacy controls on children's data.

### Aesthetic learning

A *bounded* ML layer: a small model fine-tuned per user that learns aesthetic preferences from accept/reject history. Outputs feed back into the **rule layer**, never replace it. The reasoning trail stays explainable.

## What's deliberately *not* on the roadmap

- **Infinite influencer feed.** Wearly is decision support, not a scroll.
- **Social sharing of outfits.** The user's wardrobe is their own.
- **Body image guidance.** Wearly doesn't tell users how their bodies should look.
- **One-click checkout to retailers.** Affiliate commerce is incompatible with neutral styling advice.

## How to read this roadmap

The phases are loose, not contractual. The roadmap exists to make trade-offs visible: each new feature has a phase number so you can ask "why is this here and not there?" and get a structural answer instead of a politics answer.

## Where to verify

- The canonical roadmap: `Wearly_Product_Brief.md` §13.
- The current state: `git log --oneline` + the **Status today** table above.

---

## Key terms

- **Skill package** — the `skills/wearly-styling-agent/` rule pack (8 rule files + `SKILL.md`) ([glossary](../docs/glossary.md)).
- **Result-dict contract** — the stable boundary that lets the UI and agent evolve independently ([glossary](../docs/glossary.md)).
- **Wishlist** — the locally-saved taste signal that biases future recommendations ([glossary](../docs/glossary.md)).

## Self-check

1. *(Remember)* Name one feature shipped today and one feature on the roadmap.
2. *(Understand)* Why is the result-dict contract called out as a stability anchor in the roadmap?
3. *(Apply)* Pick a roadmap item. Identify one rule pack and one chapter that would need to change to land it.

*Definitions live in the [Glossary](../docs/glossary.md). Self-check questions follow Bloom's taxonomy progression (Remember → Understand → Apply → Analyze) — the same tags used in the [Learning Graph](../docs/sims/learning-graph/index.md).*
