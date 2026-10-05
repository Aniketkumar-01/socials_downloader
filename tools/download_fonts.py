"""
Downloads Google Fonts (Outfit and JetBrains Mono) directly into frontend/fonts/
so OmniDownloader operates with zero cloud dependencies and 100% offline support.
"""

import urllib.request
from pathlib import Path

tools_dir = Path(__file__).resolve().parent
frontend_dir = tools_dir.parent / "frontend"
fonts_dir = frontend_dir / "fonts"
fonts_dir.mkdir(parents=True, exist_ok=True)

FONTS = {
    "JetBrainsMono-Regular.ttf": "https://fonts.gstatic.com/s/jetbrainsmono/v24/tDbY2o-flEEny0FZhsfKu5WU4zr3E_BX0PnT8RD8yKxjPQ.ttf",
    "JetBrainsMono-Medium.ttf": "https://fonts.gstatic.com/s/jetbrainsmono/v24/tDbY2o-flEEny0FZhsfKu5WU4zr3E_BX0PnT8RD8-qxjPQ.ttf",
    "JetBrainsMono-SemiBold.ttf": "https://fonts.gstatic.com/s/jetbrainsmono/v24/tDbY2o-flEEny0FZhsfKu5WU4zr3E_BX0PnT8RD8FqtjPQ.ttf",
    "Outfit-Regular.ttf": "https://fonts.gstatic.com/s/outfit/v15/QGYyz_MVcBeNP4NjuGObqx1XmO1I4TC1C4E.ttf",
    "Outfit-Medium.ttf": "https://fonts.gstatic.com/s/outfit/v15/QGYyz_MVcBeNP4NjuGObqx1XmO1I4QK1C4E.ttf",
    "Outfit-SemiBold.ttf": "https://fonts.gstatic.com/s/outfit/v15/QGYyz_MVcBeNP4NjuGObqx1XmO1I4e6yC4E.ttf",
    "Outfit-Bold.ttf": "https://fonts.gstatic.com/s/outfit/v15/QGYyz_MVcBeNP4NjuGObqx1XmO1I4deyC4E.ttf",
    "Outfit-ExtraBold.ttf": "https://fonts.gstatic.com/s/outfit/v15/QGYyz_MVcBeNP4NjuGObqx1XmO1I4bCyC4E.ttf",
}

def download_fonts():
    print(f"Ensuring fonts in: {fonts_dir}")
    headers = {"User-Agent": "Mozilla/5.0"}
    for filename, url in FONTS.items():
        dest = fonts_dir / filename
        if not dest.is_file() or dest.stat().st_size == 0:
            try:
                print(f"Downloading {filename}...")
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    dest.write_bytes(resp.read())
                print(f"  [OK] Saved {filename} ({dest.stat().st_size} bytes)")
            except Exception as e:
                print(f"  [WARN] Failed to download {filename}: {e}")
        else:
            print(f"  [EXISTS] {filename}")

if __name__ == "__main__":
    download_fonts()
