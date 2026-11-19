"""Heimspiel am Titelbild erkennen (für „Alle unsere Spiele am Wochenende“).

Die Wochenend-Grafik zeigt beide Wappen nebeneinander: links steht die Heimmannschaft. Ist unser weißes Wappen
(Vorlage werkzeuge/wappen_weiss.png, ausgeschnitten aus der Grafik vom 19.11.2026) in der linken Bildhälfte,
ist es ein Heimspiel. Hat die Grafik die Sponsorenleiste der 1. Mannschaft schon eingebaut (z. B. 05.11.2026),
gibt es keine zweite Leiste.

Abgleich 19.11.2026: Wochenend-Grafiken mit Wappen 0,79/0,88, alle übrigen Titelbilder höchstens 0,42;
eingebaute Leiste 0,39, ohne Leiste höchstens 0,28.
"""
import os

import numpy as np
from PIL import Image

from schheimat import _ncc

HIER = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HIER)
WAPPEN = os.path.join(HIER, "wappen_weiss.png")
LEISTE = os.path.join(REPO, "assets", "sponsorenleiste", "m1.webp")
WAPPEN_SCHWELLE = 0.6
LEISTE_SCHWELLE = 0.33
_cache = {}


def _weiss(im):
    a = np.asarray(im.convert("RGB"), dtype=float)
    hell = a.min(axis=2)
    return ((hell > 200) & (a.max(axis=2) - hell < 40)).astype(float)


def _wappen(g):
    """Bester Vergleichswert und waagerechte Lage (0 = links, 1 = rechts) unseres weißen Wappens."""
    vorlage = Image.open(WAPPEN).convert("L")
    best = (-1.0, 0.0)
    for f in np.geomspace(0.25, 0.75, 14):
        th = round(g.shape[0] * f)
        tw = round(th * vorlage.width / vorlage.height)
        if tw >= g.shape[1]:
            continue
        t = np.asarray(vorlage.resize((tw, th), Image.LANCZOS), dtype=float) / 255
        n = _ncc(g, t)
        i = np.unravel_index(n.argmax(), n.shape)
        if n[i] > best[0]:
            best = (float(n[i]), (i[1] + tw / 2) / g.shape[1])
    return best


def _leiste(im):
    """Vergleichswert der Sponsorenleiste im linken Drittel (schon im Bild?)."""
    m = Image.open(LEISTE).convert("RGBA")
    a = np.array(m)[..., 3]
    ys, xs = np.where(a > 20)
    maske = m.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)).getchannel("A")
    g = im.convert("L")
    g = g.resize((round(g.width * 400 / g.height), 400), Image.LANCZOS)
    ecke = np.asarray(g.crop((0, 0, g.width // 3, 400)), dtype=float)
    best = -1.0
    for f in np.geomspace(0.3, 0.95, 16):
        th = round(400 * f)
        tw = round(th * maske.width / maske.height)
        if tw >= ecke.shape[1]:
            continue
        best = max(best, float(_ncc(ecke, np.asarray(maske.resize((tw, th), Image.LANCZOS), dtype=float)).max()))
    return best


def heimspiel_ohne_leiste(pfad):
    """True: unser Wappen steht links (Heimspiel) und die Grafik hat noch keine Sponsorenleiste."""
    if pfad in _cache:
        return _cache[pfad]
    im = Image.open(pfad)
    g = _weiss(im.resize((round(im.width * 300 / im.height), 300), Image.LANCZOS))
    wert, x = _wappen(g)
    ergebnis = wert >= WAPPEN_SCHWELLE and x < 0.5 and _leiste(im) < LEISTE_SCHWELLE
    _cache[pfad] = ergebnis
    return ergebnis
