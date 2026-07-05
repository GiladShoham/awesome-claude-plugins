# Prompt recipes for iOS demo assets

Two prompt shapes cover most app demo needs. Swap the subject; keep the photographic framing.

## Scenes / "before" photos (rooms, exteriors)

> Photorealistic wide-angle photo of `<subject>`, `<lighting/time>`, professional real-estate
> interior photography, natural light, correct perspective, empty room.

Anchoring to architectural-photography vocabulary yields natural lighting, correct perspective,
and uncluttered compositions ready to be "redesigned."

## Product / catalog images

> Professional product photo of `<subject>`, pure white background, studio lighting, centered
> composition, soft shadow.

Studio isolation so the subject reads clearly as a catalog item.

## Example set (from the case study)

- **Rooms:** modern living room, cozy living room, master bedroom, small bedroom, modern kitchen,
  dated kitchen, bathroom, dining room, home office, open-concept living.
- **Products:** sectional sofa, coffee table, pendant light, accent chair, bookshelf, dining set,
  floor lamp, area rug, TV console, bed frame, outdoor sofa, tall planter, garden chairs, BBQ grill.
- **Exteriors:** plain garden, empty balcony, garden patio, rooftop terrace, side-yard garden.

Full case study: https://modelrunner.ai/blog/generating-demo-assets-for-an-ios-app-with-ai

## Model choice

Browse `list_models({ category: "text-to-image" })` for the current catalog and confirm price with
`get_model` — models change. Known-good picks:

- `qwen/qwen-image` — default; per-megapixel (~$0.016/image), with accurate in-image text.
- `google/imagen4/fast` — fast, cheap, photoreal; good for bulk drafts.
- `black-forest-labs/flux-2` — high prompt adherence.
- `tongyi-mai/z-image/turbo` — tuned for cost-efficient, high-volume generation.
- `krea/krea-2-large` — photoreal, when faces/materials must look real.
