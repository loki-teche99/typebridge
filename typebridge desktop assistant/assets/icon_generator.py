"""
TypeBridge Desktop - App Icon Generator
Generates high-resolution multi-size Windows icon (.ico) and PNG icon.
"""
import os
from PIL import Image, ImageDraw

def create_icon():
    assets_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(assets_dir, exist_ok=True)
    
    size = 512
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Outer rounded rectangle (background plate)
    bg_color = (20, 24, 39, 255)       # Deep slate blue
    border_color = (59, 130, 246, 255) # Electric blue border
    pad = 28
    radius = 100
    
    # Background plate
    draw.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=radius,
        fill=bg_color,
        outline=border_color,
        width=12
    )
    
    # Inner glow / gradient accent
    accent_color = (14, 165, 233, 255) # Cyan-blue
    
    # Keyboard base plate
    kb_x1 = 76
    kb_y1 = 200
    kb_x2 = size - 76
    kb_y2 = size - 80
    draw.rounded_rectangle(
        [kb_x1, kb_y1, kb_x2, kb_y2],
        radius=36,
        fill=(30, 41, 59, 255),
        outline=accent_color,
        width=8
    )
    
    # Key grid parameters
    key_fill = (51, 65, 85, 255)
    key_stroke = (99, 102, 241, 200)
    
    # Row 1 keys
    row1_y = 230
    key_w = 46
    key_h = 42
    start_x = 104
    spacing_x = 60
    for i in range(6):
        x = start_x + i * spacing_x
        draw.rounded_rectangle([x, row1_y, x + key_w, row1_y + key_h], radius=8, fill=key_fill, outline=key_stroke, width=3)
        
    # Row 2 keys
    row2_y = 290
    for i in range(6):
        x = start_x + i * spacing_x
        # highlight center key
        f = (56, 189, 248, 255) if i in (2, 3) else key_fill
        draw.rounded_rectangle([x, row2_y, x + key_w, row2_y + key_h], radius=8, fill=f, outline=key_stroke, width=3)
        
    # Spacebar row
    row3_y = 350
    draw.rounded_rectangle([start_x, row3_y, start_x + 60, row3_y + key_h], radius=8, fill=key_fill, outline=key_stroke, width=3)
    # Long spacebar
    draw.rounded_rectangle([start_x + 75, row3_y, start_x + 240, row3_y + key_h], radius=8, fill=(56, 189, 248, 255), outline=(0, 240, 255, 255), width=4)
    # Right key
    draw.rounded_rectangle([start_x + 255, row3_y, start_x + 315, row3_y + key_h], radius=8, fill=key_fill, outline=key_stroke, width=3)

    # Wireless / Bridge Waves coming out of top
    beam_color = (0, 240, 255, 255)
    
    # Wave 1 (small arc)
    draw.arc([216, 120, 296, 180], start=200, end=340, fill=beam_color, width=8)
    # Wave 2 (medium arc)
    draw.arc([180, 80, 332, 180], start=200, end=340, fill=beam_color, width=10)
    # Wave 3 (large arc)
    draw.arc([144, 40, 368, 180], start=200, end=340, fill=(99, 102, 241, 255), width=10)
    
    # Save PNG
    png_path = os.path.join(assets_dir, "icon.png")
    img.save(png_path, "PNG")
    print(f"Generated {png_path}")
    
    # Generate multi-size ICO
    ico_path = os.path.join(assets_dir, "icon.ico")
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icon_images = [img.resize(s, Image.Resampling.LANCZOS) for s in sizes]
    icon_images[0].save(
        ico_path,
        format="ICO",
        sizes=sizes,
        append_images=icon_images[1:]
    )
    print(f"Generated multi-resolution {ico_path} with sizes {sizes}")

if __name__ == "__main__":
    create_icon()
