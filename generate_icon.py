"""
Generate a minimal BabelGG icon (assets/icon.ico).
Run once: python generate_icon.py
Requires: pip install Pillow
"""
import struct, os

def make_ico():
    """Create a 32x32 dark-teal BabelGG icon as a valid .ico file."""
    size = 32
    # BGRA pixel: dark navy background with teal 'B' letter
    bg   = (46,  26,  26,  255)   # #1A1A2E in BGRA
    fg   = (168, 194, 0,   255)   # #00C2A8 in BGRA

    pixels = [bg] * (size * size)

    # Draw a simple 'B' glyph (5x7 at offset 13,12)
    glyph = [
        (0,0),(1,0),(2,0),(3,0),
        (0,1),(4,1),
        (0,2),(1,2),(2,2),(3,2),
        (0,3),(4,3),
        (0,4),(1,4),(2,4),(3,4),
        (0,5),(4,5),
        (0,6),(1,6),(2,6),(3,6),
    ]
    ox, oy = 13, 12
    for gx, gy in glyph:
        idx = (oy + gy) * size + (ox + gx)
        if 0 <= idx < len(pixels):
            pixels[idx] = fg

    # Build BMP DIB header (BITMAPINFOHEADER) for ICO
    # ICO stores XOR mask (32bpp BGRA) + AND mask (1bpp)
    width, height = size, size
    bpp    = 32
    and_row_bytes = ((width + 31) // 32) * 4
    and_size      = and_row_bytes * height
    xor_size      = width * height * 4
    dib_header    = struct.pack('<IIIHHIIIIII',
        40,            # header size
        width,
        height * 2,    # double height for XOR+AND
        1,             # color planes
        bpp,
        0,             # BI_RGB
        xor_size,
        0, 0, 0, 0
    )
    # XOR mask (bottom-up)
    xor_data = b''
    for row in reversed(range(height)):
        for col in range(width):
            b, g, r, a = pixels[row * width + col]
            xor_data += bytes([b, g, r, a])
    # AND mask (all zeros = fully opaque)
    and_data = b'\x00' * and_size

    img_data = dib_header + xor_data + and_data
    img_size = len(img_data)

    # ICO file header + directory entry
    ico_header = struct.pack('<HHH', 0, 1, 1)   # reserved, type=1 (ICO), count=1
    offset = 6 + 16   # header + 1 dir entry
    dir_entry = struct.pack('<BBBBHHII',
        width, height, 0, 0, 1, bpp, img_size, offset
    )
    return ico_header + dir_entry + img_data


os.makedirs('assets', exist_ok=True)
ico_bytes = make_ico()
with open('assets/icon.ico', 'wb') as f:
    f.write(ico_bytes)
print(f'assets/icon.ico written ({len(ico_bytes)} bytes)')
