"""Генерирует packaging/Sotto.icns: эмодзи 🎙 на скруглённой плашке через AppKit.

Запуск: .venv/bin/python scripts/make_icon.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import AppKit
from Foundation import NSMakeRect

SIZES = [16, 32, 64, 128, 256, 512, 1024]
OUT = Path(__file__).resolve().parent.parent / "packaging" / "Sotto.icns"


def render_png(size: int, path: Path) -> None:
    image = AppKit.NSImage.alloc().initWithSize_((size, size))
    image.lockFocus()

    radius = size * 0.22
    rect = NSMakeRect(size * 0.05, size * 0.05, size * 0.9, size * 0.9)
    bg = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(rect, radius, radius)
    AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(0.13, 0.13, 0.16, 1.0).setFill()
    bg.fill()

    text = "🎙"
    font = AppKit.NSFont.systemFontOfSize_(size * 0.62)
    attrs = {AppKit.NSFontAttributeName: font}
    s = AppKit.NSAttributedString.alloc().initWithString_attributes_(text, attrs)
    ts = s.size()
    s.drawAtPoint_(((size - ts.width) / 2, (size - ts.height) / 2))

    image.unlockFocus()

    tiff = image.TIFFRepresentation()
    rep = AppKit.NSBitmapImageRep.imageRepWithData_(tiff)
    rep.setSize_((size, size))
    png = rep.representationUsingType_properties_(AppKit.NSBitmapImageFileTypePNG, None)
    png.writeToFile_atomically_(str(path), True)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        iconset = Path(tmp) / "Sotto.iconset"
        iconset.mkdir()
        for size in SIZES:
            if size <= 512:
                render_png(size, iconset / f"icon_{size}x{size}.png")
            if size >= 32:
                render_png(size, iconset / f"icon_{size // 2}x{size // 2}@2x.png")
        OUT.parent.mkdir(exist_ok=True)
        subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(OUT)], check=True)
    print(f"OK: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
