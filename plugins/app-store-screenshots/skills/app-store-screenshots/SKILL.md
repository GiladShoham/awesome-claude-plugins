---
name: app-store-screenshots
description: >-
  Generate polished App Store / Google Play marketing screenshots from raw app captures —
  device mockups, on-brand backgrounds, and ASO-aware headlines, kept visually consistent
  across the whole set. Powered by ModelRunner (https://modelrunner.ai). Use when the user
  wants to turn app screenshots into store marketing images, create a cohesive screenshot set
  for an app listing, add device frames or headlines to captures, or prepare App Store /
  Google Play screenshot uploads.
---

# App Store Screenshots

Turn raw in-app captures into a **cohesive set** of App Store / Google Play marketing
screenshots — each a device mockup on a designed background with an ASO-aware headline, all
sharing one visual language. Runs on **[ModelRunner](https://modelrunner.ai)** via its public
MCP, using the purpose-built `modelrunner/app-store-screenshot-composer` wrapper, which encodes
the consistency workflow so you don't have to hand-design each image. If your app already calls
ModelRunner, this reuses the same API key and request/poll pattern — no new integration.

> Powered by ModelRunner — one API for image, video, audio, 3D, and text. Case study:
> https://modelrunner.ai/blog/generating-app-store-screenshots-with-ai-home-redesign-app-case-study

## Prerequisites

1. **The ModelRunner MCP must be connected.** These steps call the tools `create_upload_url`,
   `run_model`, `wait_for_request`, and `get_wrapper`. If they are unavailable, connect the
   server at `https://mcp.modelrunner.run/mcp` (authorize with your ModelRunner account when prompted; keep a small balance at
   https://modelrunner.ai). In Claude Code: `claude mcp add --transport http modelrunner https://mcp.modelrunner.run/mcp`.
2. **A shell** for streaming file bytes (`curl`). Screenshots are uploaded out-of-band, never
   sent through the model as tokens.

## Inputs to gather

Ask the user for whatever is missing:

- **Raw screenshots** — file paths (clean in-app captures, e.g. 1242×2688). One per store slide.
- **App name** and a one-line **feature description per screen** (grounds styling + headlines).
- **Brand color** — hex. Pull it from the app's own theme source (a `*Theme.swift`, a Color asset,
  or design tokens) before asking — in the case study the brand teal `#0E9F94` came straight from
  `RoomixTheme.swift`.
- **Target device(s)** — e.g. `iphone_6_5`, `ipad_13` (see `references/device-dimensions.md`).
- **Headlines/subheadlines** — optional; the wrapper auto-generates if omitted, but supplying
  ASO-aware copy is stronger (see `references/aso-copy-guide.md`).

## Before the first run: read the live schema

Call `get_wrapper` for `modelrunner/app-store-screenshot-composer` (or `get_wrapper_raw_schema` for
the full, untruncated enums) and confirm the current **`device` enum**, `layout`, and
`background_style` values. Enums can change; never hard-code them blind. The `device` enum now
spans portrait, landscape, and alt-resolution variants (e.g. `iphone_6_5`, `iphone_6_5_1284`,
`ipad_13`, `ipad_13_2064`, plus their `_landscape` forms). See `references/wrapper-schema.md` for
the field guide + gotchas — notably: `iphone_6_9` is the schema **default** but is **not in the
enum**, so passing it explicitly fails validation; pick a listed value like `iphone_6_5`.

## The workflow — anchor first, then style-reference the rest

This is the load-bearing pattern that makes the set consistent. **Do not parallelize the whole
batch** — the hero must exist first.

### Phase 0 — Upload each capture (parallel)
For every screenshot:
1. `create_upload_url({ fileName: "<meaningful-name>.png" })` → `{ upload_url, relay_upload_url, file_url }`.
2. `curl -X PUT -T <path> -H "Content-Type: image/png" "<upload_url>"` (on a 403
   `host_not_allowed`, retry the PUT against `relay_upload_url`).
3. Keep the returned `file_url`.

**Name files meaningfully** — `home-feed.png`, `redesign-config.png`, not `IMG_0042.png`. The
wrapper reads the filename as a semantic hint for styling and headline relevance.

### Phase 1 — Hero (sequential, one image, the anchor)
Run screenshot #1 with **NO** `style_reference`:
```
run_model({
  endpoint: "modelrunner/app-store-screenshot-composer",
  input: {
    screenshot: "<hero file_url>",
    headline: "<hero headline>",
    subheadline: "<hero subheadline>",
    device: "iphone_6_5",
    layout: "text_top",
    brand_color: "#0E9F94",
    background_style: "gradient_vibrant",
    variants: 1
    // base_model: "openai/gpt-image-2/edit"   // optional override; strong text + UI redraw
  }
})
```
`wait_for_request` → the terminal payload's `output` is a `string[]`; take `output[0]` as the
**anchor URL**. Phase 2 depends on it — hard barrier.

### Phase 2 — The rest (parallel)
For every remaining screenshot, run with `style_reference` set to the **anchor URL** — always
the same anchor, never chain to the previous output:
```
input: { screenshot: "<file_url>", headline: "…", subheadline: "…", device: "iphone_6_5",
         layout: "text_top", brand_color: "#0E9F94", background_style: "gradient_vibrant",
         variants: 1, style_reference: "<anchor URL>" }
```
`wait_for_request` each, then `curl -o <name>.png "<output[0]>"` to save. All of phase 2 can run
concurrently — total wall-clock ≈ the slowest single render.

### Repeat per device
Run the whole anchor→style-reference cycle once per target device (e.g. `iphone_6_5` then
`ipad_13`), so each device set is internally consistent.

## Writing the copy

Keep the same shared controls (`brand_color`, `background_style`, `layout`) across every render —
that is the cohesion lever. Lead each headline with a searchable benefit noun-phrase and spread
the app's keyword cluster across slides without repetition. Full guidance:
`references/aso-copy-guide.md`.

## Cost

~$0.035–0.15 per generated image depending on the base model — the wrapper's default base averages
~$0.035/run, while `openai/gpt-image-2/edit` (the premium, text-faithful option) bills $0.151 per
output. Each `variants` output is billed separately, so set `variants: 1` for the cheapest run. In
the case study, a full set of 12 screenshots (6 iPhone + 6 iPad) came to ≈ $1.66. Confirm live
pricing from `get_wrapper` / the request's `totalPrice`.

## Output

Report the saved file paths + the ModelRunner request IDs (from each `wait_for_request`) so the
run is reproducible. Store dimensions are validated by App Store Connect — check the produced
sizes against `references/device-dimensions.md`.
