# Device dimensions & the wrapper `device` enum

The `modelrunner/app-store-screenshot-composer` wrapper renders to fixed device canvases. Always
confirm the **live** `device` enum with `get_wrapper` (or `get_wrapper_raw_schema` for the full,
untruncated list) before a run — the values below are a guide, not a contract.

## Live enum values (verify before use)

| `device` value | Orientation | Output size |
|---|---|---|
| `iphone_6_5` | portrait | 1242 × 2688 |
| `iphone_6_5_landscape` | landscape | 2688 × 1242 |
| `iphone_6_5_1284` | portrait | 1284 × 2778 |
| `iphone_6_5_1284_landscape` | landscape | 2778 × 1284 |
| `ipad_13` | portrait | 2048 × 2732 |
| `ipad_13_landscape` | landscape | 2732 × 2048 |
| `ipad_13_2064` | portrait | 2064 × 2752 |
| `ipad_13_2064_landscape` | landscape | 2752 × 2064 |

In the case study, the `iphone_6_5` and `ipad_13` outputs landed a few pixels under target
(~1232 × 2688 and ~2048 × 2720) and still passed App Store Connect's dimension validation.

## Gotcha: `iphone_6_9`

`iphone_6_9` (1290 × 2796) is the wrapper's schema **default** but is **not one of the enum's
allowed values**, so passing it explicitly fails validation. Use a listed value such as
`iphone_6_5` for the iPhone portrait slot. Re-check against `get_wrapper_raw_schema` — this may
change.

## App Store Connect (reference)

Apple's required screenshot set changes over time — check the current "screenshot specifications"
in App Store Connect. As of writing, a 6.9"/6.5" iPhone portrait set and a 13" iPad portrait set
cover current devices:

- iPhone 6.9" — 1290 × 2796
- iPhone 6.5" — 1242 × 2688
- iPad 13" — 2048 × 2732

## Google Play (reference)

Play Store phone screenshots: 320–3840px on any edge, 16:9 or 9:16 aspect, 2–8 images. A portrait
render at ~1242 × 2688 satisfies Play as-is.
