// Wearly — Post-Presentation Deck
// 9 slides, designed for both email attachment and LinkedIn document upload.
//
// Palette: Wearly brand (matte black on white + warm terracotta accent)
//   primary  #111111  matte black (Wearly wordmark + dark slides)
//   surface  #FFFFFF  white (content cards)
//   subtle   #FAFAFA  off-white (slide backgrounds)
//   accent   #9F5A36  warm terracotta (one accent moment per slide)
//   muted    #6B6B6B  secondary text
//   rule     #EEEEEE  separator gray
//
// Typography: Georgia (serif headers) + Calibri (clean body).

const pptxgen = require("pptxgenjs");

const COLOR = {
  ink:      "111111",
  white:    "FFFFFF",
  surface:  "FAFAFA",
  accent:   "9F5A36",
  accent2:  "C17F5A",
  muted:    "6B6B6B",
  rule:     "EEEEEE",
  paper:    "F5F1EA",
};

const FONT = {
  serif: "Georgia",
  sans:  "Calibri",
};

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";        // 10" x 5.625"
pres.author = "Eatedal Alfadhel";
pres.title  = "Wearly — Evidence-informed personal styling agent";
pres.company = "University of St. Thomas · SEIS 666";

// ─────────────────────────────────────────────
// Helper: page-number / footer (light slides only)
// ─────────────────────────────────────────────
function addFooter(slide, n) {
  slide.addText(`Wearly  ·  SEIS 666  ·  Eatedal Alfadhel`, {
    x: 0.5, y: 5.2, w: 5, h: 0.3,
    fontFace: FONT.sans, fontSize: 9, color: COLOR.muted,
    align: "left", valign: "middle", margin: 0,
  });
  slide.addText(`${n} / 9`, {
    x: 8.5, y: 5.2, w: 1, h: 0.3,
    fontFace: FONT.sans, fontSize: 9, color: COLOR.muted,
    align: "right", valign: "middle", margin: 0,
  });
}

// ─────────────────────────────────────────────
// Helper: numbered chip + title (content slides)
// ─────────────────────────────────────────────
function addChipTitle(slide, num, eyebrow, title) {
  // Eyebrow chip (number / section label) — top-left
  slide.addText(`${num}  ·  ${eyebrow.toUpperCase()}`, {
    x: 0.5, y: 0.4, w: 9, h: 0.3,
    fontFace: FONT.sans, fontSize: 10, color: COLOR.accent,
    bold: true, charSpacing: 4, align: "left", valign: "middle", margin: 0,
  });
  // Title (serif)
  slide.addText(title, {
    x: 0.5, y: 0.75, w: 9, h: 0.85,
    fontFace: FONT.serif, fontSize: 34, color: COLOR.ink,
    align: "left", valign: "top", margin: 0,
  });
  // Thin rule under header zone (NOT under the title — under the whole header band)
  slide.addShape(pres.shapes.LINE, {
    x: 0.5, y: 1.75, w: 9, h: 0,
    line: { color: COLOR.rule, width: 1 },
  });
}

// ═════════════════════════════════════════════════════════════════
// Slide 1 — Cover (matte black)
// ═════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: COLOR.ink };

  // Eyebrow
  s.addText("AN EVIDENCE-INFORMED PERSONAL STYLING AGENT", {
    x: 0.6, y: 1.1, w: 8.8, h: 0.3,
    fontFace: FONT.sans, fontSize: 10, color: COLOR.accent2,
    bold: true, charSpacing: 6, align: "left", valign: "middle", margin: 0,
  });

  // Wordmark — large serif
  s.addText("Wearly", {
    x: 0.6, y: 1.5, w: 8.8, h: 1.9,
    fontFace: FONT.serif, fontSize: 110, color: COLOR.white,
    italic: false, align: "left", valign: "middle", margin: 0,
  });

  // Accent rule
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: 3.6, w: 0.6, h: 0.04,
    fill: { color: COLOR.accent2 }, line: { color: COLOR.accent2, width: 0 },
  });

  // Subtitle
  s.addText([
    { text: "A body-positive, agent-shaped styling system.\n",
      options: { fontSize: 17, color: COLOR.white, breakLine: true } },
    { text: "Built end-to-end as a Streamlit app, an Intelligent Book, and a structured Knowledge Graph.",
      options: { fontSize: 13, color: "BFBFBF" } },
  ], {
    x: 0.6, y: 3.7, w: 8.8, h: 1.0,
    fontFace: FONT.sans, align: "left", valign: "top", margin: 0,
  });

  // Attribution band — bottom
  s.addText([
    { text: "Eatedal Alfadhel",
      options: { bold: true, color: COLOR.white, fontSize: 12 } },
    { text: "   ·   SEIS 666  ·  Digital Transformation with AI   ·   University of St. Thomas   ·   2026",
      options: { color: "BFBFBF", fontSize: 11 } },
  ], {
    x: 0.6, y: 5.05, w: 8.8, h: 0.4,
    fontFace: FONT.sans, align: "left", valign: "middle", margin: 0,
  });
}

// ═════════════════════════════════════════════════════════════════
// Slide 2 — The problem
// ═════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: COLOR.surface };
  addChipTitle(s, "01", "The problem", "Outfit decisions cost time every morning.");

  // Left column — stat callouts
  s.addText("24h", {
    x: 0.5, y: 2.05, w: 3.5, h: 1.0,
    fontFace: FONT.serif, fontSize: 76, color: COLOR.ink,
    align: "left", valign: "top", margin: 0,
  });
  s.addText("per year of friction\nfor a daily 3–4-minute decision.", {
    x: 0.5, y: 3.15, w: 3.5, h: 0.7,
    fontFace: FONT.sans, fontSize: 11, color: COLOR.muted,
    align: "left", valign: "top", margin: 0,
  });

  s.addShape(pres.shapes.LINE, {
    x: 4.25, y: 2.1, w: 0, h: 2.6,
    line: { color: COLOR.rule, width: 1 },
  });

  // Right column — narrative
  s.addText([
    { text: "A generic chatbot can't reason about ",
      options: { color: COLOR.ink, fontSize: 14 } },
    { text: "your fit profile, ", options: { bold: true, color: COLOR.ink, fontSize: 14 } },
    { text: "today's ", options: { color: COLOR.ink, fontSize: 14 } },
    { text: "weather, ", options: { bold: true, color: COLOR.ink, fontSize: 14 } },
    { text: "your ", options: { color: COLOR.ink, fontSize: 14 } },
    { text: "calendar, ", options: { bold: true, color: COLOR.ink, fontSize: 14 } },
    { text: "the items in ", options: { color: COLOR.ink, fontSize: 14 } },
    { text: "your closet, ", options: { bold: true, color: COLOR.ink, fontSize: 14 } },
    { text: "or what ", options: { color: COLOR.ink, fontSize: 14 } },
    { text: "color palette ", options: { bold: true, color: COLOR.ink, fontSize: 14 } },
    { text: "your skin tone reads best in. It can't see the gap before you stand in front of your closet.\n\n", options: { color: COLOR.ink, fontSize: 14 } },
    { text: "Wearly is built around the gap. ",
      options: { italic: true, color: COLOR.accent, fontSize: 14, bold: true } },
    { text: "It reads the actual context first, then reasons against your wardrobe with cited styling rules.",
      options: { italic: true, color: COLOR.ink, fontSize: 14 } },
  ], {
    x: 4.55, y: 2.05, w: 5.0, h: 2.7,
    fontFace: FONT.sans, align: "left", valign: "top", margin: 0, lineSpacing: 22,
  });

  addFooter(s, 2);
}

// ═════════════════════════════════════════════════════════════════
// Slide 3 — An agent, not a chatbot
// ═════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: COLOR.surface };
  addChipTitle(s, "02", "Positioning", "An agent — not a chatbot.");

  // Comparison columns
  const colTop = 2.0, colH = 2.85;

  // LEFT — Chatbot
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.5, y: colTop, w: 4.3, h: colH,
    fill: { color: COLOR.white },
    line: { color: COLOR.rule, width: 1 },
  });
  s.addText("Generic chatbot", {
    x: 0.7, y: colTop + 0.15, w: 4.0, h: 0.4,
    fontFace: FONT.sans, fontSize: 11, color: COLOR.muted, bold: true,
    charSpacing: 3, align: "left", valign: "middle", margin: 0,
  });
  s.addText([
    { text: "Stateless prompt-response", options: { bullet: true, breakLine: true } },
    { text: "No memory across sessions", options: { bullet: true, breakLine: true } },
    { text: "Can't read calendar, weather, wardrobe", options: { bullet: true, breakLine: true } },
    { text: "Output is text only — no reasoning trail", options: { bullet: true, breakLine: true } },
    { text: "No reject-and-regenerate loop", options: { bullet: true } },
  ], {
    x: 0.75, y: colTop + 0.6, w: 3.9, h: 2.2,
    fontFace: FONT.sans, fontSize: 12, color: COLOR.ink,
    valign: "top", margin: 0, paraSpaceAfter: 4,
  });

  // RIGHT — Wearly
  s.addShape(pres.shapes.RECTANGLE, {
    x: 5.2, y: colTop, w: 4.3, h: colH,
    fill: { color: COLOR.ink },
    line: { color: COLOR.ink, width: 0 },
  });
  s.addText("Wearly — the agent", {
    x: 5.4, y: colTop + 0.15, w: 4.0, h: 0.4,
    fontFace: FONT.sans, fontSize: 11, color: COLOR.accent2, bold: true,
    charSpacing: 3, align: "left", valign: "middle", margin: 0,
  });
  s.addText([
    { text: "Context-first stance — reads profile, calendar, weather, wardrobe before deciding", options: { bullet: true, breakLine: true } },
    { text: "Seven-step reasoning loop with visible per-step trail", options: { bullet: true, breakLine: true } },
    { text: "Cites a named rule for every decision (<pack>#R<N>)", options: { bullet: true, breakLine: true } },
    { text: "Reject-and-regenerate — learns from each rejection", options: { bullet: true, breakLine: true } },
    { text: "Stateful across sessions — wear history, profile, wishlist", options: { bullet: true } },
  ], {
    x: 5.45, y: colTop + 0.6, w: 4.0, h: 2.2,
    fontFace: FONT.sans, fontSize: 12, color: COLOR.white,
    valign: "top", margin: 0, paraSpaceAfter: 4,
  });

  addFooter(s, 3);
}

// ═════════════════════════════════════════════════════════════════
// Slide 4 — The seven-step workflow
// ═════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: COLOR.surface };
  addChipTitle(s, "03", "How the agent thinks", "The seven-step workflow.");

  const steps = [
    ["1", "Load profile", "fit profile · skin-tone palette · preferences"],
    ["2", "Read context", "calendar event · weather snapshot · occasion tag"],
    ["3", "Filter wardrobe", "by occasion · weather band · rotation freshness"],
    ["4", "Build outfit", "dress or top + bottom · accessories · shoes"],
    ["5", "Score colors", "skin-tone palette · best / good / avoid tiers"],
    ["6", "Check fit + gaps", "silhouette rules · required pieces per occasion"],
    ["7", "Emit reasoning", "cited rules · trade-offs · wardrobe-gap flags"],
  ];

  const stepTop = 2.0;
  const rowH = 0.42;
  for (let i = 0; i < steps.length; i++) {
    const [num, label, sub] = steps[i];
    const y = stepTop + i * rowH;

    // Step-number badge
    s.addShape(pres.shapes.OVAL, {
      x: 0.5, y: y + 0.04, w: 0.32, h: 0.32,
      fill: { color: COLOR.ink },
      line: { color: COLOR.ink, width: 0 },
    });
    s.addText(num, {
      x: 0.5, y: y + 0.04, w: 0.32, h: 0.32,
      fontFace: FONT.sans, fontSize: 11, color: COLOR.white, bold: true,
      align: "center", valign: "middle", margin: 0,
    });

    // Step label (bold) + sub (muted)
    s.addText([
      { text: label, options: { bold: true, color: COLOR.ink, fontSize: 13 } },
      { text: "   " + sub, options: { color: COLOR.muted, fontSize: 11 } },
    ], {
      x: 1.0, y: y, w: 8.5, h: 0.4,
      fontFace: FONT.sans, align: "left", valign: "middle", margin: 0,
    });
  }

  // Bottom strapline
  s.addText("Every step writes a line to the reasoning trail the user can read.", {
    x: 0.5, y: 5.05, w: 9, h: 0.3,
    fontFace: FONT.sans, fontSize: 11, color: COLOR.accent,
    italic: true, align: "left", valign: "middle", margin: 0,
  });

  addFooter(s, 4);
}

// ═════════════════════════════════════════════════════════════════
// Slide 5 — What makes Wearly different
// ═════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: COLOR.surface };
  addChipTitle(s, "04", "Differentiation", "Three commitments the runtime enforces.");

  const pillars = [
    {
      h: "Evidence-informed",
      sub: "Every rule traces to a verified source",
      body: "Eight rule packs cite Vasileva 2018, Han 2017, Itten's color theory, the McGuire body-shape framework, GDPR-aligned privacy guidance, and more. Citations live in rule_refs.py and the reasoning trail prints the slug on every line.",
    },
    {
      h: "Body-positive contract",
      sub: "Enforced at the prose layer",
      body: "Wearly never names a 'flaw to hide.' Every fit-advice sentence reframes negative shape language as silhouette-emphasis language. Enforced by an integration test — not a stylistic guideline.",
    },
    {
      h: "Auditable by design",
      sub: "Reasoning lines cite named rules",
      body: "Every decision a reviewer can trace to its citation. The Wearly Knowledge Graph (91 nodes / 187 typed edges) is the structured-knowledge substrate a future RAG or LLM shopping layer can query along its edges.",
    },
  ];

  const cardTop = 1.95;
  const cardW = 3.0, cardH = 3.05, cardGap = 0.13;
  const startX = 0.5;

  for (let i = 0; i < pillars.length; i++) {
    const x = startX + i * (cardW + cardGap);
    // Card
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: cardTop, w: cardW, h: cardH,
      fill: { color: COLOR.white },
      line: { color: COLOR.rule, width: 1 },
    });
    // Accent rule (top-left)
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: cardTop, w: 0.55, h: 0.06,
      fill: { color: COLOR.accent }, line: { color: COLOR.accent, width: 0 },
    });
    // Pillar number
    s.addText(`0${i + 1}`, {
      x: x + 0.2, y: cardTop + 0.18, w: 1.5, h: 0.3,
      fontFace: FONT.sans, fontSize: 10, color: COLOR.accent, bold: true,
      charSpacing: 4, align: "left", valign: "middle", margin: 0,
    });
    // Heading
    s.addText(pillars[i].h, {
      x: x + 0.2, y: cardTop + 0.5, w: cardW - 0.4, h: 0.5,
      fontFace: FONT.serif, fontSize: 19, color: COLOR.ink, bold: false,
      align: "left", valign: "top", margin: 0,
    });
    // Subhead
    s.addText(pillars[i].sub, {
      x: x + 0.2, y: cardTop + 1.0, w: cardW - 0.4, h: 0.32,
      fontFace: FONT.sans, fontSize: 10.5, color: COLOR.muted, italic: true,
      align: "left", valign: "top", margin: 0,
    });
    // Body
    s.addText(pillars[i].body, {
      x: x + 0.2, y: cardTop + 1.4, w: cardW - 0.4, h: 1.55,
      fontFace: FONT.sans, fontSize: 11, color: COLOR.ink,
      align: "left", valign: "top", margin: 0, lineSpacing: 16,
    });
  }

  addFooter(s, 5);
}

// ═════════════════════════════════════════════════════════════════
// Slide 6 — The Intelligent Book
// ═════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: COLOR.surface };
  addChipTitle(s, "05", "Intelligent textbook", "A Level-2 book built around the agent.");

  // Left — narrative
  s.addText([
    { text: "Wearly ships as a ", options: { color: COLOR.ink, fontSize: 13 } },
    { text: "Level-2 intelligent textbook ", options: { bold: true, color: COLOR.ink, fontSize: 13 } },
    { text: "(McCreary's framework): a concept-graph-driven, MicroSim-equipped, evidence-citable companion to the running app.\n\n",
      options: { color: COLOR.ink, fontSize: 13 } },
    { text: "Every chapter ends with a Bloom-tagged self-check and a glossary footer. The Wearly Knowledge Graph is queryable from the book and embedded in the app.",
      options: { color: COLOR.muted, fontSize: 12 } },
  ], {
    x: 0.5, y: 2.0, w: 4.5, h: 2.9,
    fontFace: FONT.sans, align: "left", valign: "top", margin: 0, lineSpacing: 20,
  });

  // Right — tile grid (2 cols × 3 rows)
  const tiles = [
    ["11", "chapters", "Part I · the agent end-to-end"],
    ["8",  "styling refs", "Part II · color · fit · context · etc."],
    ["91", "graph nodes", "Wearly Knowledge Graph"],
    ["187","typed edges", "domain × user × runtime"],
    ["2",  "MicroSims", "color harmony · freshness"],
    ["1",  "evidence ch.", "Part III · provenance & sources"],
  ];

  const gridX = 5.4, gridY = 2.0;
  const tileW = 2.05, tileH = 0.92, gap = 0.10;
  for (let i = 0; i < tiles.length; i++) {
    const r = Math.floor(i / 2);
    const c = i % 2;
    const x = gridX + c * (tileW + gap);
    const y = gridY + r * (tileH + gap);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y, w: tileW, h: tileH,
      fill: { color: COLOR.white }, line: { color: COLOR.rule, width: 1 },
    });
    // Big number
    s.addText(tiles[i][0], {
      x: x + 0.15, y: y + 0.08, w: 0.85, h: 0.65,
      fontFace: FONT.serif, fontSize: 30, color: COLOR.ink, bold: false,
      align: "left", valign: "middle", margin: 0,
    });
    // Label + sub
    s.addText([
      { text: tiles[i][1] + "\n",
        options: { bold: true, color: COLOR.ink, fontSize: 10.5, breakLine: true } },
      { text: tiles[i][2], options: { color: COLOR.muted, fontSize: 9 } },
    ], {
      x: x + 1.0, y: y + 0.13, w: tileW - 1.1, h: 0.72,
      fontFace: FONT.sans, align: "left", valign: "middle", margin: 0,
      lineSpacing: 13,
    });
  }

  addFooter(s, 6);
}

// ═════════════════════════════════════════════════════════════════
// Slide 7 — The Wearly Knowledge Graph
// ═════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: COLOR.surface };
  addChipTitle(s, "06", "Structured knowledge", "The Wearly Knowledge Graph.");

  // Stat row
  const statTop = 2.0;
  const stats = [
    ["91",  "nodes",         "Three layers · one schema."],
    ["187", "typed edges",   "OWNS · REQUIRES · USES_RULE · POWERS · …"],
    ["3",   "layers",        "domain · user behavior · runtime"],
  ];
  for (let i = 0; i < 3; i++) {
    const x = 0.5 + i * 3.07;
    s.addText(stats[i][0], {
      x, y: statTop, w: 1.3, h: 1.1,
      fontFace: FONT.serif, fontSize: 60, color: COLOR.ink, bold: false,
      align: "left", valign: "top", margin: 0,
    });
    s.addText(stats[i][1], {
      x: x + 1.35, y: statTop + 0.15, w: 1.6, h: 0.4,
      fontFace: FONT.sans, fontSize: 10, color: COLOR.accent, bold: true,
      charSpacing: 3, align: "left", valign: "middle", margin: 0,
    });
    s.addText(stats[i][2], {
      x: x + 1.35, y: statTop + 0.55, w: 1.65, h: 0.7,
      fontFace: FONT.sans, fontSize: 10.5, color: COLOR.muted,
      align: "left", valign: "top", margin: 0, lineSpacing: 14,
    });
  }

  // Separator
  s.addShape(pres.shapes.LINE, {
    x: 0.5, y: 3.4, w: 9, h: 0,
    line: { color: COLOR.rule, width: 1 },
  });

  // Body paragraph
  s.addText([
    { text: "Bigger circles = signals the user produced more of. ",
      options: { bold: true, color: COLOR.ink, fontSize: 13 } },
    { text: "A piece worn six times across three occasions grows. A color the closet keeps returning to grows. An occasion attended often grows. ",
      options: { color: COLOR.ink, fontSize: 13 } },
    { text: "Domain archetypes stay quiet so the user-behavior layer reads first.\n\n",
      options: { color: COLOR.ink, fontSize: 13 } },
    { text: "RAG-ready. ", options: { bold: true, color: COLOR.accent, fontSize: 12 } },
    { text: "Every edge is typed — a future LLM shopping or explainer agent can traverse the graph along named edges rather than vector-searching free text.",
      options: { color: COLOR.muted, fontSize: 12 } },
  ], {
    x: 0.5, y: 3.55, w: 9, h: 1.5,
    fontFace: FONT.sans, align: "left", valign: "top", margin: 0, lineSpacing: 18,
  });

  addFooter(s, 7);
}

// ═════════════════════════════════════════════════════════════════
// Slide 8 — Architecture & tech
// ═════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: COLOR.surface };
  addChipTitle(s, "07", "Engineering", "How it's built.");

  // Layer stack — visual
  const layers = [
    ["UI",        "Streamlit app  ·  6 main pages  ·  user-menu dropdown",          COLOR.ink],
    ["Agent",     "Seven-step run_agent() loop  ·  reject-and-regenerate",          COLOR.ink],
    ["Tools",     "weather  ·  calendar  ·  color  ·  fit  ·  wardrobe  ·  history  ·  shopping",  COLOR.accent],
    ["Rules",     "Eight rule packs (Claude Skill spec)  ·  every decision cited",  COLOR.ink],
    ["Knowledge", "Wearly Knowledge Graph  ·  vis-network.js  ·  91 nodes / 187 edges", COLOR.ink],
    ["Persistence","Local JSON on device  ·  no cloud account  ·  opt-in user overlay", COLOR.ink],
  ];

  const layTop = 1.95, layH = 0.42, layGap = 0.04;
  for (let i = 0; i < layers.length; i++) {
    const y = layTop + i * (layH + layGap);
    // Label column
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.5, y, w: 1.6, h: layH,
      fill: { color: layers[i][2] }, line: { color: layers[i][2], width: 0 },
    });
    s.addText(layers[i][0], {
      x: 0.5, y, w: 1.6, h: layH,
      fontFace: FONT.sans, fontSize: 11, color: COLOR.white, bold: true,
      charSpacing: 3, align: "center", valign: "middle", margin: 0,
    });
    // Body column
    s.addShape(pres.shapes.RECTANGLE, {
      x: 2.15, y, w: 7.35, h: layH,
      fill: { color: COLOR.white }, line: { color: COLOR.rule, width: 1 },
    });
    s.addText(layers[i][1], {
      x: 2.3, y, w: 7.1, h: layH,
      fontFace: FONT.sans, fontSize: 11.5, color: COLOR.ink,
      align: "left", valign: "middle", margin: 0,
    });
  }

  // Bottom row — verification badges
  const badges = [
    "393 tests passing",
    "mkdocs strict build",
    "live on Streamlit Cloud",
    "deployed via GitHub Pages",
  ];
  const badgeY = 4.85, badgeH = 0.32, badgeW = 2.13, badgeGap = 0.10;
  for (let i = 0; i < badges.length; i++) {
    const x = 0.5 + i * (badgeW + badgeGap);
    s.addShape(pres.shapes.RECTANGLE, {
      x, y: badgeY, w: badgeW, h: badgeH,
      fill: { color: COLOR.paper }, line: { color: COLOR.rule, width: 1 },
    });
    s.addText(badges[i], {
      x, y: badgeY, w: badgeW, h: badgeH,
      fontFace: FONT.sans, fontSize: 10, color: COLOR.ink, bold: true,
      align: "center", valign: "middle", margin: 0,
    });
  }

  addFooter(s, 8);
}

// ═════════════════════════════════════════════════════════════════
// Slide 9 — See it live (closing, matte black)
// ═════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: COLOR.ink };

  // Eyebrow
  s.addText("EXPLORE WEARLY", {
    x: 0.6, y: 0.7, w: 8.8, h: 0.3,
    fontFace: FONT.sans, fontSize: 10, color: COLOR.accent2,
    bold: true, charSpacing: 6, align: "left", valign: "middle", margin: 0,
  });

  // Title
  s.addText("See it live.", {
    x: 0.6, y: 1.0, w: 8.8, h: 1.0,
    fontFace: FONT.serif, fontSize: 54, color: COLOR.white,
    align: "left", valign: "top", margin: 0,
  });

  // Accent rule
  s.addShape(pres.shapes.RECTANGLE, {
    x: 0.6, y: 2.05, w: 0.55, h: 0.04,
    fill: { color: COLOR.accent2 }, line: { color: COLOR.accent2, width: 0 },
  });

  // Link rows
  const links = [
    ["Live app",          "styling-agent-64jigzmqms4v7f9ugou8bv.streamlit.app",      "An agent runs end-to-end."],
    ["Intelligent Book",  "eatedalsf.github.io/styling-agent",                       "11 chapters · 8 styling refs · Knowledge Graph."],
    ["Source code",       "github.com/eatedalsf/styling-agent",                      "MIT · 393 tests · Claude Skill spec."],
  ];

  const linkTop = 2.4, linkH = 0.74, linkGap = 0.06;
  for (let i = 0; i < links.length; i++) {
    const y = linkTop + i * (linkH + linkGap);
    // Card
    s.addShape(pres.shapes.RECTANGLE, {
      x: 0.6, y, w: 8.8, h: linkH,
      fill: { color: "1A1A1A" }, line: { color: "2A2A2A", width: 1 },
    });
    // Label
    s.addText(links[i][0], {
      x: 0.85, y: y + 0.08, w: 2.5, h: 0.3,
      fontFace: FONT.sans, fontSize: 10, color: COLOR.accent2, bold: true,
      charSpacing: 4, align: "left", valign: "middle", margin: 0,
    });
    // URL
    s.addText(links[i][1], {
      x: 0.85, y: y + 0.32, w: 7.0, h: 0.32,
      fontFace: "Consolas", fontSize: 13, color: COLOR.white, bold: false,
      align: "left", valign: "middle", margin: 0,
    });
    // Tagline
    s.addText(links[i][2], {
      x: 0.85, y: y + 0.5, w: 7.5, h: 0.22,
      fontFace: FONT.sans, fontSize: 9.5, color: "9A9A9A", italic: true,
      align: "left", valign: "top", margin: 0,
    });
  }

  // Sign-off
  s.addText("Eatedal Alfadhel  ·  SEIS 666  ·  University of St. Thomas  ·  2026", {
    x: 0.6, y: 5.05, w: 8.8, h: 0.4,
    fontFace: FONT.sans, fontSize: 10, color: "9A9A9A",
    align: "left", valign: "middle", margin: 0,
  });
}

// ─────────────────────────────────────────────
// Write
// ─────────────────────────────────────────────
pres.writeFile({ fileName: "Wearly-Post-Presentation.pptx" })
    .then(p => console.log("Wrote:", p));
