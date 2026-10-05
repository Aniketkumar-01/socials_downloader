"""
OmniDownloader - Application Icon Generator
Generates high-resolution multi-size Windows icon (app.ico) and application logo (app.png).
Loads from artifact source if available, or renders a clean vector-styled gradient glyph with Pillow.
"""

import os
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent
assets_dir = root_dir / "assets"
assets_dir.mkdir(parents=True, exist_ok=True)

ico_target = assets_dir / "app.ico"
png_target = assets_dir / "app.png"

# Potential artifact paths from IDE generation
artifact_candidates = [
    Path(r"C:\Users\anike\.gemini\antigravity-ide\brain\c7909c13-4416-4d4b-a597-1631d8bd9c01\app_icon_1791192255990.jpg"),
    assets_dir / "raw_icon.png",
    assets_dir / "raw_icon.jpg",
]

def generate_with_pillow():
    try:
        from PIL import Image, ImageDraw, ImageFilter
    except ImportError:
        print("[WARN] Pillow is not installed. Installing Pillow or using Windows fallback...")
        return False

    base_img = None
    for cand in artifact_candidates:
        if cand.is_file():
            try:
                base_img = Image.open(cand).convert("RGBA")
                print(f"[INFO] Loaded source icon from: {cand}")
                break
            except Exception as e:
                print(f"[WARN] Failed to load {cand}: {e}")

    if not base_img:
        print("[INFO] Rendering native gradient squircle icon from scratch...")
        size = 512
        base_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(base_img)

        # 1. Dark squircle background
        margin = 32
        squircle_box = [margin, margin, size - margin, size - margin]
        draw.rounded_rectangle(squircle_box, radius=96, fill=(18, 20, 29, 255), outline=(50, 56, 82, 255), width=3)

        # 2. Glowing cyan/purple download arrow
        # Arrow stem: center x=256, width=64, top=140, bottom=300
        stem_left = 224
        stem_right = 288
        stem_top = 130
        stem_bottom = 290

        # Arrow head: triangle pointing down
        arrow_head = [
            (170, 270),  # left tip
            (342, 270),  # right tip
            (256, 370),  # bottom tip
        ]

        # Draw vibrant gradient glow
        for glow_w in range(12, 0, -2):
            alpha = int(40 - glow_w * 2.5)
            draw.rounded_rectangle(
                [stem_left - glow_w, stem_top - glow_w, stem_right + glow_w, stem_bottom + glow_w],
                radius=12,
                outline=(56, 189, 248, alpha),
                width=glow_w
            )

        # Solid arrow stem with cyan/violet
        draw.rounded_rectangle([stem_left, stem_top, stem_right, stem_bottom], radius=10, fill=(99, 102, 241, 255))
        draw.polygon(arrow_head, fill=(56, 189, 248, 255))

        # Bottom baseline / tray
        tray_left = 160
        tray_right = 352
        tray_top = 400
        tray_bottom = 416
        draw.rounded_rectangle([tray_left, tray_top, tray_right, tray_bottom], radius=8, fill=(168, 85, 247, 255))

    # Resize and export PNG
    png_256 = base_img.resize((256, 256), Image.Resampling.LANCZOS)
    png_256.save(png_target, "PNG")
    print(f"[SUCCESS] Exported high-res PNG to: {png_target}")

    # Export multi-resolution ICO
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    png_256.save(ico_target, format="ICO", sizes=icon_sizes)
    print(f"[SUCCESS] Exported multi-resolution Windows ICO to: {ico_target}")
    return True

def generate_with_powershell():
    """Windows native .NET fallback if Pillow is unavailable."""
    ico_path = str(ico_target).replace("\\", "\\\\")
    png_path = str(png_target).replace("\\", "\\\\")
    ps_cmd = f"""
Add-Type -AssemblyName System.Drawing
$width = 256
$height = 256
$bmp = New-Object System.Drawing.Bitmap($width, $height)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$brush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 18, 20, 29))
$g.FillRectangle($brush, 0, 0, $width, $height)

$arrowBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(255, 56, 189, 248))
$points = @(
    (New-Object System.Drawing.Point(128, 190)),
    (New-Object System.Drawing.Point(64, 130)),
    (New-Object System.Drawing.Point(100, 130)),
    (New-Object System.Drawing.Point(100, 50)),
    (New-Object System.Drawing.Point(156, 50)),
    (New-Object System.Drawing.Point(156, 130)),
    (New-Object System.Drawing.Point(192, 130))
)
$g.FillPolygon($arrowBrush, $points)

$hIcon = $bmp.GetHicon()
$icon = [System.Drawing.Icon]::FromHandle($hIcon)
$fs = New-Object System.IO.FileStream('{ico_path}', [System.IO.FileMode]::Create)
$icon.Save($fs)
$fs.Close()
$bmp.Save('{png_path}', [System.Drawing.Imaging.ImageFormat]::Png)
$g.Dispose()
$bmp.Dispose()
Write-Host "Native PowerShell icon generation complete."
"""
    try:
        import subprocess
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True)
        return True
    except Exception as e:
        print(f"[ERROR] PowerShell fallback failed: {e}")
        return False

if __name__ == "__main__":
    if not generate_with_pillow():
        generate_with_powershell()
