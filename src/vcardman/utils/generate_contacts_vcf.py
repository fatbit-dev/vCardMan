import base64
import hashlib
import random
import zlib
import struct

OUTFILE = "contacts_20_with_photos.vcf"

FIRST_NAMES = [
    "Lucia","Daniel","Sofia","Jonas","Camille",
    "Ethan","Maya","Rafael","Olivia","Kenji",
    "Isabel","Wei","Aarav","Emma","Freja",
    "Omar","Petra","Tiago","Chloe","Mateo"
]

LAST_NAMES = [
    "Garcia","Martin","Rossi","Mueller","Dubois",
    "Smith","Kowalski","Silva","Brown","Nakamura",
    "Lopez","Chen","Patel","Johnson","Andersen",
    "Ibrahim","Novak","Ferreira","Wilson","Santos"
]


def png_chunk(tag, data):
    crc = zlib.crc32(tag + data) & 0xffffffff
    return (
        struct.pack(">I", len(data)) +
        tag +
        data +
        struct.pack(">I", crc)
    )


def generate_avatar(seed, size=64):
    h = hashlib.sha256(seed.encode()).digest()

    c1 = (h[0], h[1], h[2])
    c2 = (h[3], h[4], h[5])

    rows = []

    for y in range(size):
        row = bytearray()

        for x in range(size):
            symmetric_x = min(x, size - 1 - x)

            bit = (h[(symmetric_x // 4) % len(h)] >> (y % 8)) & 1

            color = c1 if bit else c2

            row.extend(color)

        rows.append(bytes(row))

    raw = b''.join(b'\x00' + r for r in rows)

    png = (
        b'\x89PNG\r\n\x1a\n' +
        png_chunk(
            b'IHDR',
            struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
        ) +
        png_chunk(b'IDAT', zlib.compress(raw, 9)) +
        png_chunk(b'IEND', b'')
    )

    return base64.b64encode(png).decode()


with open(OUTFILE, "w", encoding="utf-8") as f:

    for i in range(20):

        first = FIRST_NAMES[i]
        last = LAST_NAMES[i]

        full = f"{first} {last}"

        avatar = generate_avatar(full)

        f.write(f"""BEGIN:VCARD
VERSION:3.0
N:{last};{first};;;
FN:{full}
ORG:Example Corporation
TITLE:Engineer
ROLE:Professional Contact
EMAIL;TYPE=WORK:{first.lower()}.{last.lower()}@example.com
EMAIL;TYPE=HOME:{first.lower()}@personal.example
TEL;TYPE=WORK:+34-91-555-{1000+i}
TEL;TYPE=CELL:+34-600-555-{1000+i}
ADR;TYPE=WORK:;;Example Street {i+1};Madrid;Madrid;2800{i%10};Spain
URL:https://example.com
BDAY:1990-01-{(i%28)+1:02d}
UID:contact-{i+1}
PHOTO;ENCODING=b;TYPE=PNG:{avatar}
END:VCARD

""")

print(f"Created {OUTFILE}")
