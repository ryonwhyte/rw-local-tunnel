#!/usr/bin/env python3
"""
Create application icon for RW Local Tunnel
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    """Create a modern icon for the application"""

    # Create icon in multiple sizes
    sizes = [16, 32, 48, 64, 128, 256, 512]

    for size in sizes:
        # Create a new image with transparency
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Calculate dimensions
        padding = size // 8
        circle_bbox = [padding, padding, size - padding, size - padding]

        # Draw gradient-like background circle
        # Outer circle (darker blue)
        draw.ellipse([padding-2, padding-2, size-padding+2, size-padding+2],
                     fill=(0, 60, 120, 255))
        # Inner circle (lighter blue)
        draw.ellipse(circle_bbox, fill=(0, 120, 215, 255))

        # Draw network/tunnel symbol
        center = size // 2

        # Draw connection dots (nodes)
        node_size = size // 12
        node_offset = size // 3

        # Left node (source)
        draw.ellipse([center - node_offset - node_size, center - node_size,
                     center - node_offset + node_size, center + node_size],
                    fill=(255, 255, 255, 255))

        # Right node (destination)
        draw.ellipse([center + node_offset - node_size, center - node_size,
                     center + node_offset + node_size, center + node_size],
                    fill=(255, 255, 255, 255))

        # Draw tunnel line (with arrow)
        line_width = max(2, size // 32)
        arrow_size = size // 8

        # Main line
        draw.line([center - node_offset + node_size, center,
                  center + node_offset - node_size, center],
                 fill=(255, 255, 255, 255), width=line_width)

        # Arrow head pointing right
        arrow_x = center + node_offset - node_size - arrow_size
        draw.polygon([
            (arrow_x, center - arrow_size // 2),
            (arrow_x + arrow_size, center),
            (arrow_x, center + arrow_size // 2)
        ], fill=(255, 255, 255, 255))

        # Add "T" text for smaller sizes or network symbol for larger
        if size >= 128:
            # Draw additional network lines for detail
            line_offset = size // 6
            thin_width = max(1, size // 64)

            # Top connection line
            draw.line([center - node_offset, center - line_offset,
                      center + node_offset, center - line_offset],
                     fill=(255, 255, 255, 128), width=thin_width)

            # Bottom connection line
            draw.line([center - node_offset, center + line_offset,
                      center + node_offset, center + line_offset],
                     fill=(255, 255, 255, 128), width=thin_width)

        # Save icon
        filename = f"rw-tunnel-{size}.png"
        img.save(filename, 'PNG')
        print(f"✅ Created {filename}")

    # Create the main icon file (256x256 for Linux desktop)
    os.system("cp rw-tunnel-256.png rw-local-tunnel.png")

    # Create ICO file for Windows compatibility (if needed)
    img_256 = Image.open("rw-tunnel-256.png")
    img_128 = Image.open("rw-tunnel-128.png")
    img_64 = Image.open("rw-tunnel-64.png")
    img_48 = Image.open("rw-tunnel-48.png")
    img_32 = Image.open("rw-tunnel-32.png")
    img_16 = Image.open("rw-tunnel-16.png")

    img_256.save("rw-local-tunnel.ico", format='ICO',
                sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print("✅ Created rw-local-tunnel.ico")

    print("\n🎨 Icons created successfully!")
    print("Main icon: rw-local-tunnel.png")
    print("Windows icon: rw-local-tunnel.ico")

if __name__ == "__main__":
    create_icon()