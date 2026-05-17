# Wearly — Press Kit

Materials for sharing the Wearly project after the SEIS 666 final presentation.
Designed for two uses:

- **Email** — attach the deck, paste the email template body.
- **LinkedIn (Prof Daniel)** — upload the PPTX directly to LinkedIn as a
  *document* post (these get the highest engagement on LinkedIn); paste
  the LinkedIn caption.

## What's in this folder

| File | Purpose |
|---|---|
| `Wearly-Post-Presentation.pptx` | 9-slide deck — the main shareable asset. Open in PowerPoint to preview, edit, or export to PDF. |
| `email-template.md` | Email body ready to send to Prof Daniel. |
| `linkedin-captions.md` | Three caption variants (short / medium / long) for the prof's LinkedIn post. |
| `screenshot-shot-list.md` | Six specific app + book screenshots to capture, with caption text — paste them into the deck OR send as separate images. |
| `build_deck.js` | Source for the PPTX (in case you want to tweak text or colors). Rebuild with `node build_deck.js`. |

## How to use this kit

### Step 1 — Take 6 screenshots (5 minutes)

Open `screenshot-shot-list.md` and capture the six images it describes.
Save them in `press-kit/screenshots/` with the filenames listed.

### Step 2 — Send the email to Prof Daniel

Open `email-template.md`, fill in the bracketed fields, attach the PPTX
(and optionally the screenshots), and send.

### Step 3 — Hand the prof one of the captions

Paste one of the three captions from `linkedin-captions.md` into the
email body so the prof can copy-paste it directly when posting on
LinkedIn. Three lengths — pick the one closest to the prof's usual
posting style.

## Editing the deck

The PPTX was generated from `build_deck.js` with [pptxgenjs](https://gitbrent.github.io/PptxGenJS/).
To regenerate after any edits:

```powershell
cd press-kit
node build_deck.js
```

Or open the PPTX directly in PowerPoint and edit text inline — every
text block is a normal PowerPoint text box.
