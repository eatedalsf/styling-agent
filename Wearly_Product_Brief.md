# Wearly AI Product Brief

> Single source of truth for the Wearly AI product vision.
> This document drives all subsequent design, engineering, and roadmap decisions.

---

## 1. Product Name

The product name is **Wearly AI**.

---

## 2. Product Identity

Wearly AI is a **mobile-first, clean luxury, professional personal styling agent**. It helps busy women choose complete outfits using their real wardrobe, calendar, weather, location, body measurements, fit preferences, wear history, and favorite stores.

The product should later expand to support men, children, and family styling workflows, including helping parents coordinate outfits for their children.

---

## 3. Target User

The initial target user is **women with busy schedules** who need quick, context-aware outfit decisions for work, school, errands, appointments, travel, social events, and formal occasions.

Future versions should support:

- men,
- children,
- family profiles, and
- parent-managed child wardrobes.

---

## 4. Product Goal

The goal is to make outfit planning **faster, more personal, and more context-aware**.

Wearly AI should **not** behave like a generic fashion chatbot. It should behave like an **agent** that reasons through:

- calendar context,
- weather,
- wardrobe availability,
- fit profile,
- wear history, and
- shopping preferences

before recommending an outfit.

---

## 5. UI Direction

The interface should be:

- mobile-first,
- clean luxury,
- professional,
- calm,
- polished,
- card-based,
- easy to use, and
- suitable for a premium lifestyle/productivity app.

It should **not** feel like a technical dashboard.

---

## 6. Realism Level

Treat this as a **realistic, product-quality prototype**, not a simple class demo.

Use real or realistic structured data. The product should feel like an early MVP that could eventually be launched.

---

## 7. Core Feature Areas

### 7.1 Calendar Integration

Wearly AI should support:

- manual event entry,
- Google Calendar integration or Google Calendar-ready architecture,
- Apple Calendar / iPhone support through `.ics` upload in the prototype, and
- future native iOS Calendar permission-based integration.

The agent should use:

- event title,
- time,
- location,
- description,
- dress code (if available), and
- event type

to infer **occasion, formality, and styling needs**.

### 7.2 Weather and Location

Wearly AI should support:

- manual city selection,
- optional current-location detection,
- fallback to manual city entry if automatic location fails,
- weather-based outfit reasoning, and
- privacy notes explaining that location is used only for outfit planning.

Weather should influence clothing choices such as **layers, shoes, fabrics, and outerwear**.

### 7.3 Digital Wardrobe Builder

Users should be able to build their wardrobe by:

- uploading or taking photos of clothing items,
- removing the item background and replacing it with a white background,
- adding items from product URLs from online stores, and
- manually adding items.

Each wardrobe item should include metadata such as:

- category,
- color,
- season,
- formality,
- fabric,
- comfort,
- modesty,
- fit,
- occasion suitability,
- availability,
- image,
- source, and
- ownership status.

### 7.4 Favorite Stores and Shopping

Users should be able to add favorite stores and shopping websites.

If the user has an event but does not own suitable pieces, Wearly AI should:

- identify wardrobe gaps,
- recommend missing pieces,
- prioritize the user's preferred stores,
- distinguish between **owned items** and **suggested-to-buy items**, and
- allow saving suggestions to a wishlist or shopping list.

### 7.5 Fit and Body Profile

Users should be able to **optionally** enter measurements and fit preferences.

The profile may include:

- height,
- shoulder width,
- bust / chest,
- waist,
- hips,
- inseam,
- preferred fit,
- modesty preference,
- comfort needs,
- style goals,
- areas to highlight, and
- areas to balance.

**The language must be body-positive. Never describe body features as flaws.**

Use language such as:

- highlight preferred features,
- balance proportions,
- support the user's preferred silhouette,
- improve comfort, and
- increase confidence.

The agent should use fit profile data in its reasoning **and** in its final explanation.

### 7.6 Wear History

Each wardrobe item should track:

- how many times it has been worn,
- last worn date,
- event or occasion,
- location,
- outfit pairing,
- user feedback, and
- availability status.

Wearly AI should use wear history to:

- avoid overusing the same item too often,
- suggest underused items when appropriate, and
- explain when wear history affects the recommendation.

### 7.7 Reject and Regenerate

Users should be able to reject:

- a single item,
- multiple items, or
- the full outfit.

Rejection reasons may include:

- wore it recently,
- too formal,
- too casual,
- uncomfortable,
- not suitable for weather,
- does not fit well,
- not modest enough,
- do not like this color today,
- unavailable, or
- in laundry.

After rejection, the agent should **regenerate a better recommendation and explain what changed and why**.

### 7.8 Agentic Reasoning Trace

The app must clearly show that Wearly AI is an **agent, not a chatbot**.

The reasoning trace should include:

1. Read event or user request.
2. Determine occasion and formality.
3. Check calendar.
4. Check weather and location.
5. Load wardrobe.
6. Load fit / body profile.
7. Apply styling rules.
8. Check color coordination.
9. Check wear history and availability.
10. Detect wardrobe gaps.
11. Recommend outfit.
12. Allow rejection and regeneration.

### 7.9 Before/After Demo

The project should include a clear before/after demo.

- **Before** — A generic chatbot gives a simple, generic outfit suggestion.
- **After** — Wearly AI uses calendar, weather, wardrobe, fit profile, wear history, and favorite stores to create a personalized outfit with reasoning and alternatives.

---

## 8. Intelligent Book

Later, the repository should include a mini **Intelligent Book**.

The Intelligent Book should explain:

- product vision,
- user problem,
- agent workflow,
- styling knowledge base,
- wardrobe intelligence,
- fit profile logic,
- calendar and weather context,
- shopping gap logic,
- before/after demo,
- privacy and security, and
- product roadmap.

The Intelligent Book **supports** the working app but does not replace it.

---

## 9. Knowledge Graph

Later, the repository should include a **knowledge graph** that models relationships between:

- calendar events,
- weather,
- wardrobe items,
- fit profile,
- user preferences,
- wear history,
- outfit recommendations,
- wardrobe gaps,
- shopping suggestions, and
- feedback.

The knowledge graph should help demonstrate that Wearly AI **reasons through connected context** rather than producing random outfit advice.

---

## 10. Agent Skills

Later, the repository should include a `skills/` folder with a **Wearly Styling Agent Skill**.

The skill package should include:

- `SKILL.md`,
- occasion rules,
- weather rules,
- fit and silhouette rules,
- wardrobe filtering rules,
- color coordination rules,
- wear history rules,
- shopping gap rules, and
- privacy guidelines.

---

## 11. Scientific and Expert Logic

Wearly AI's recommendation logic should **not** be based only on generic prompting.

It should combine:

- evidence-informed fashion recommendation research,
- color harmony principles,
- body-positive fit and silhouette rules,
- occasion and formality rules,
- weather and location constraints,
- wardrobe availability,
- wear history,
- user rejection reasons, and
- user feedback.

### 11.1 References (placeholder)

> *This section is reserved for future academic and expert references — peer-reviewed research, color theory sources, fit and silhouette literature, and styling industry frameworks. To be populated as the product matures.*

---

## 12. SEIS 666 Alignment

This project is for **SEIS 666 — Digital Transformation with AI**.

- **Final project:** Build Something That Reasons.
- **Track:** Track B — Agentic AI System.

The project must demonstrate:

- a working system,
- a multi-step workflow,
- at least two tools or data sources,
- a documented decision process,
- error handling,
- a before/after comparison,
- GitHub documentation, and
- a 10-minute demo.

---

## 13. Product Roadmap

| Phase | Scope |
|---|---|
| **Phase 0** | Fix current repo reliability. |
| **Phase 1** | Rebrand and improve the current demo. |
| **Phase 2** | Add product-grade mobile-first UI and user profile. |
| **Phase 3** | Add wardrobe builder, fit profile, wear history, and reject/regenerate. |
| **Phase 4** | Add shopping, wishlist, and favorite stores. |
| **Phase 5** | Add Intelligent Book, Knowledge Graph, and Skills. |
| **Phase 6** | Add production roadmap for real Google Calendar, Apple Calendar, image processing, store integrations, mobile app, privacy, and family profiles. |

---

*This document is the single source of truth for the Wearly AI product vision. All design, engineering, and roadmap decisions should align with this brief.*
