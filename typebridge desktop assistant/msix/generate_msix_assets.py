"""
MSIX Asset Generator for TypeBridge
Generates all required visual assets for Windows App SDK / MSIX package.
"""
import os
from PIL import Image

def generate_assets():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    assets_dir = os.path.join(base_dir, "Assets")
    os.makedirs(assets_dir, exist_ok=True)

    src_icon_path = os.path.abspath(os.path.join(base_dir, "..", "assets", "icon.png"))
    if not os.path.exists(src_icon_path):
        raise FileNotFoundError(f"Source icon not found at {src_icon_path}")

    icon = Image.open(src_icon_path).convert("RGBA")

    # 1. StoreLogo: 50x50
    store_logo = icon.resize((50, 50), Image.Resampling.LANCZOS)
    store_logo.save(os.path.join(assets_dir, "StoreLogo.png"), "PNG")
    print("Generated StoreLogo.png (50x50)")

    # 2. Square44x44Logo: 44x44
    sq44 = icon.resize((44, 44), Image.Resampling.LANCZOS)
    sq44.save(os.path.join(assets_dir, "Square44x44Logo.png"), "PNG")
    print("Generated Square44x44Logo.png (44x44)")

    # Targetsize variants for 44x44 (recommended for taskbar/start list)
    for ts in [16, 24, 32, 48, 256]:
        ts_img = icon.resize((ts, ts), Image.Resampling.LANCZOS)
        ts_img.save(os.path.join(assets_dir, f"Square44x44Logo.targetsize-{ts}.png"), "PNG")
        # Altform unplated
        ts_img.save(os.path.join(assets_dir, f"Square44x44Logo.altform-unplated_targetsize-{ts}.png"), "PNG")

    # 3. Square150x150Logo: 150x150
    sq150 = icon.resize((150, 150), Image.Resampling.LANCZOS)
    sq150.save(os.path.join(assets_dir, "Square150x150Logo.png"), "PNG")
    print("Generated Square150x150Logo.png (150x150)")

    # 4. Square71x71Logo: 71x71 (small tile)
    sq71 = icon.resize((71, 71), Image.Resampling.LANCZOS)
    sq71.save(os.path.join(assets_dir, "Square71x71Logo.png"), "PNG")
    print("Generated Square71x71Logo.png (71x71)")

    # 4b. Square310x310Logo: 310x310 (large tile)
    sq310 = icon.resize((310, 310), Image.Resampling.LANCZOS)
    sq310.save(os.path.join(assets_dir, "Square310x310Logo.png"), "PNG")
    print("Generated Square310x310Logo.png (310x310)")

    # 5. Wide310x150Logo: 310x150 (centered icon with transparent or brand background)
    wide = Image.new("RGBA", (310, 150), (11, 15, 25, 255))
    # Place 120x120 icon in center
    icon_wide = icon.resize((120, 120), Image.Resampling.LANCZOS)
    wide.paste(icon_wide, ((310 - 120) // 2, (150 - 120) // 2), icon_wide)
    wide.save(os.path.join(assets_dir, "Wide310x150Logo.png"), "PNG")
    print("Generated Wide310x150Logo.png (310x150)")

    # 6. SplashScreen: 620x300 (centered icon with brand background)
    splash = Image.new("RGBA", (620, 300), (11, 15, 25, 255))
    icon_splash = icon.resize((200, 200), Image.Resampling.LANCZOS)
    splash.paste(icon_splash, ((620 - 200) // 2, (300 - 200) // 2), icon_splash)
    splash.save(os.path.join(assets_dir, "SplashScreen.png"), "PNG")
    print("Generated SplashScreen.png (620x300)")

    print(f"All MSIX visual assets generated in {assets_dir}")

if __name__ == "__main__":
    generate_assets()
