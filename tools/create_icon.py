"""
OmniDownloader - Application Icon Generator (Tool)
Generates high-resolution multi-size Windows icon (app.ico) and application logo (app.png).
Saves directly into the assets/ directory.
"""

from pathlib import Path

tools_dir = Path(__file__).resolve().parent
root_dir = tools_dir.parent
assets_dir = root_dir / "assets"
assets_dir.mkdir(parents=True, exist_ok=True)

ico_target = assets_dir / "app.ico"
png_target = assets_dir / "app.png"

artifact_candidates = [
    assets_dir / "raw_icon.png",
    assets_dir / "raw_icon.jpg",
]

def generate_with_pillow():
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return False

    base_img = None
    for cand in artifact_candidates:
        if cand.is_file():
            try:
                base_img = Image.open(cand).convert("RGBA")
                break
            except Exception:
                pass

    if not base_img:
        size = 512
        base_img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(base_img)

        # 1. Dark squircle background
        margin = 32
        squircle_box = [margin, margin, size - margin, size - margin]
        draw.rounded_rectangle(squircle_box, radius=96, fill=(18, 20, 29, 255), outline=(50, 56, 82, 255), width=3)

        # 2. Cyan/indigo download glyph
        stem_left = 224
        stem_right = 288
        stem_top = 130
        stem_bottom = 290

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

        draw.rounded_rectangle([stem_left, stem_top, stem_right, stem_bottom], radius=10, fill=(99, 102, 241, 255))
        draw.polygon(arrow_head, fill=(56, 189, 248, 255))

        # Bottom baseline
        tray_left = 160
        tray_right = 352
        tray_top = 400
        tray_bottom = 416
        draw.rounded_rectangle([tray_left, tray_top, tray_right, tray_bottom], radius=8, fill=(168, 85, 247, 255))

    # Resize and export PNG
    png_256 = base_img.resize((256, 256), Image.Resampling.LANCZOS)
    png_256.save(png_target, "PNG")

    # Export multi-resolution ICO
    icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
    png_256.save(ico_target, format="ICO", sizes=icon_sizes)
    print(f"[SUCCESS] Exported icon to: {ico_target}")
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
