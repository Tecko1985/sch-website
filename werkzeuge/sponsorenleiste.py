"""Sponsorenleiste aus einem Logo-Bild mit einfarbigem Hintergrund bauen (lokal, braucht Pillow und numpy).
Aufruf: python3 werkzeuge/sponsorenleiste.py LOGOS.png assets/sponsorenleiste/<mannschaft>.png TAFEL.png
Die Logos müssen 2 x 2 angeordnet sein wie im Bild der Ersten (Bereiche unten ggf. anpassen)."""
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ein, frei_pfad, tafel_pfad = sys.argv[1:4]
im = np.array(Image.open(ein).convert("RGB")).astype(float)
bg = im[5, 5].copy()

# Farbe -> Transparenz (wie „Farbe zu Alpha“ in GIMP): weiche Kanten bleiben erhalten
oben = np.where(im > bg, (im - bg) / np.maximum(255 - bg, 1), (bg - im) / np.maximum(bg, 1))
alpha = np.clip(oben.max(axis=2), 0, 1)
farbe = np.where(alpha[..., None] > 0, (im - bg) / np.maximum(alpha[..., None], 1e-6) + bg, 0)
rgba = np.dstack([np.clip(farbe, 0, 255), alpha * 255]).astype(np.uint8)
frei = Image.fromarray(rgba)

# Die vier Logos (2 x 2 im Eingabebild): Bereiche grob, danach eng auf den Inhalt zuschneiden
bereiche = [(0, 0, 900, 420), (900, 0, 1920, 420), (0, 440, 990, 745), (900, 700, 1920, 1080)]
logos = []
for b in bereiche:
    teil = frei.crop(b)
    a = np.array(teil)[..., 3]
    ys, xs = np.where(a > 12)
    logos.append(teil.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)))

BREIT, RAND, ABSTAND = 420, 24, 46
skaliert = []
for lg in logos:
    h = round(lg.height * BREIT / lg.width)
    skaliert.append(lg.resize((BREIT, h), Image.LANCZOS))

schrift = None
for f in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", "/System/Library/Fonts/Helvetica.ttc"):
    try:
        schrift = ImageFont.truetype(f, 34)
        break
    except OSError:
        pass
text = "PRÄSENTIERT VON"
tb = ImageDraw.Draw(Image.new("RGBA", (10, 10))).textbbox((0, 0), text, font=schrift)
th = tb[3] - tb[1]

hoehe = RAND + th + 30 + sum(l.height for l in skaliert) + ABSTAND * (len(skaliert) - 1) + RAND
for pfad, mit_tafel in ((frei_pfad, False), (tafel_pfad, True)):
    leinwand = Image.new("RGBA", (BREIT + 2 * RAND, hoehe), (0, 0, 0, 0))
    d = ImageDraw.Draw(leinwand)
    if mit_tafel:
        d.rounded_rectangle((0, 0, leinwand.width - 1, leinwand.height - 1), radius=26, fill=(27, 45, 79, 235))
    # Schrift mit leichtem Schatten, damit sie auch ohne Tafel auf hellen Bildern lesbar ist
    if not mit_tafel:
        d.text((RAND + 2, RAND - tb[1] + 2), text, font=schrift, fill=(0, 0, 0, 140))
    d.text((RAND, RAND - tb[1]), text, font=schrift, fill=(255, 255, 255, 255))
    y = RAND + th + 30
    for lg in skaliert:
        if not mit_tafel:  # weicher dunkler Schatten unter den Logos
            schatten = Image.new("RGBA", lg.size, (0, 0, 0, 0))
            schatten.putalpha(lg.getchannel("A").point(lambda v: int(v * 0.45)))
            leinwand.alpha_composite(Image.merge("RGBA", (*[Image.new("L", lg.size, 0)] * 3, schatten.getchannel("A"))), (RAND + 3, y + 3))
        leinwand.alpha_composite(lg, (RAND, y))
        y += lg.height + ABSTAND
    leinwand.save(pfad)
    print(pfad, leinwand.size)
