---
name: ios-demo-assets
description: >-
  Bulk-generate demo/sample images for an iOS app with AI and load them into Xcode's
  Assets.xcassets and the iOS Simulator's Photos library. Powered by ModelRunner
  (https://modelrunner.ai). Use when the user needs sample photos to exercise a photo-driven
  iOS feature, wants to populate the Simulator photo picker, or needs on-spec placeholder
  images for an Xcode project.
---

# iOS Demo Assets

Generate a batch of on-spec demo images with AI and get them **Xcode-ready** (valid
`Assets.xcassets` bundles) and **Simulator-ready** (in the Photos library) in one pass. Runs on
**[ModelRunner](https://modelrunner.ai)** text-to-image via its public MCP. Every asset is just
a prompt, so the whole library is reproducible and versionable in git — the same API key and
request/poll pattern your app already uses, ModelRunner as dev infrastructure rather than just a
user-facing backend.

> Powered by ModelRunner — one API for image, video, audio, 3D, and text. Case study:
> https://modelrunner.ai/blog/generating-demo-assets-for-an-ios-app-with-ai

## Prerequisites

1. **The ModelRunner MCP must be connected** — tools `run_model`, `wait_for_request` (and
   `list_models` to browse). Connect `https://mcp.modelrunner.run/mcp` (authorize with your ModelRunner account; keep a small balance at
   https://modelrunner.ai). Claude Code: `claude mcp add --transport http modelrunner https://mcp.modelrunner.run/mcp`.
2. **Xcode + a booted iOS Simulator**, and a shell for `curl` / `xcrun`.

## Step 1 — Plan the set

Agree the categories, counts, and **kebab-case asset names** up front — they become `.imageset`
folder names and SwiftUI `Image("Group/name")` keys. Example layout:

```
Assets.xcassets/
├── SampleRooms/        room-living-modern.imageset, room-kitchen-modern.imageset, …
├── SampleProducts/
│   ├── Interior/       product-sectional-sofa.imageset, product-floor-lamp.imageset, …
│   └── Exterior/       product-outdoor-sofa.imageset, …
└── Exterior/           exterior-garden-plain.imageset, exterior-balcony-empty.imageset, …
```

## Step 2 — Generate (async, parallel)

Browse the live catalog with `list_models({ category: "text-to-image" })` and confirm pricing with
`get_model` — the catalog changes. Known-good picks: **`qwen/qwen-image`** (default; per-megapixel,
with accurate in-image text), `google/imagen4/fast` (fast, cheap, photoreal), `black-forest-labs/flux-2`
(strong prompt adherence), plus newer volume/photoreal options such as `tongyi-mai/z-image/turbo`
(tuned for cost-efficient bulk) or `krea/krea-2-large` (photoreal). For faces/hands where realism
must be exact, a follow-up edit pass helps. For each asset:

1. `run_model({ endpoint: "qwen/qwen-image", input: { prompt } })` → returns a `requestId`
   immediately (async queue).
2. `wait_for_request({ requestId })` → the terminal `output` is a `string[]`; take `output[0]`.
3. `curl -L -o <path>.jpg "<output[0]>"`.

Submit the **whole batch concurrently** — each request resolves independently, so a 20–30 image
library finishes in a few minutes rather than serially. Prompt recipes (photoreal scenes vs.
white-background product shots) are in `references/prompt-recipes.md`.

## Step 3 — Write into Assets.xcassets

For each downloaded image, build a valid image set:
```bash
python3 scripts/make_imageset.py <image.jpg> <Assets.xcassets/Group/name>
```
It creates `<name>.imageset/` containing the image plus a `Contents.json` that Xcode's asset
catalog compiler understands. The image is then addressable in SwiftUI as `Image("Group/name")`.

## Step 4 — Push into the Simulator's Photos library

The in-app photo picker (`PhotosPicker`) reads the **Simulator Photos library**, not
`Assets.xcassets`. Get the booted device UDID and add the media:
```bash
xcrun simctl list devices booted          # copy the UDID
scripts/add_to_simulator.sh <UDID> <one-or-more .jpg files>
```
`add_to_simulator.sh` wraps `xcrun simctl addmedia`. The Photos library is **per-simulator**, so
re-run this against each new simulator UDID — the `xcassets` copy stays the durable source of truth.

## Reproducibility, cost, output

- **Keep the prompts in git** next to the app. Need a warmer palette or a localized set? Re-run
  the same batch — no stock-photo relicensing or re-shoot.
- **Cost** is per-megapixel on `qwen/qwen-image` (~$0.016/image) — a flat, known price for a full
  regeneration; confirm live with `get_model`.
- **Report** the asset names + ModelRunner request IDs + output URLs so the run is reproducible.
- **Scale** — in the case study this produced 29 assets across 4 categories in under 10 minutes of
  wall-clock (parallel generation), replacing 54 hand-picked stock PNGs and shrinking the bundle.
