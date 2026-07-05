#!/usr/bin/env python3
"""Create a valid Xcode `.imageset` bundle from a single image.

Usage:
    python3 make_imageset.py <image> <dest-base-without-extension>

Example:
    python3 make_imageset.py room-living-modern.jpg \\
        MyApp/Assets.xcassets/SampleRooms/room-living-modern

Produces:
    MyApp/Assets.xcassets/SampleRooms/room-living-modern.imageset/
        room-living-modern.jpg
        Contents.json

The image is then addressable in SwiftUI as `Image("SampleRooms/room-living-modern")`
(the group folder must be a "Provides Namespace" folder, or reference by the leaf name).

A single universal, unscaled image is emitted (Xcode "Single Scale") so there are no
missing-2x/3x warnings — correct for photographic demo assets.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


def make_imageset(image_path: Path, dest_base: Path) -> Path:
    imageset = dest_base.with_suffix(".imageset")
    imageset.mkdir(parents=True, exist_ok=True)
    filename = image_path.name
    shutil.copy2(image_path, imageset / filename)
    contents = {
        "images": [{"idiom": "universal", "filename": filename}],
        "info": {"version": 1, "author": "xcode"},
    }
    (imageset / "Contents.json").write_text(json.dumps(contents, indent=2) + "\n")
    return imageset


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    image_path = Path(argv[1])
    dest_base = Path(argv[2])
    if not image_path.is_file():
        print(f"error: image not found: {image_path}", file=sys.stderr)
        return 1
    imageset = make_imageset(image_path, dest_base)
    print(f"wrote {imageset}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
