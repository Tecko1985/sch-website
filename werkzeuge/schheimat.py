"""SCHeimat-Zeichen (unten rechts, mit schwarzem Schleier) in Galerie- und Beitragsbilder setzen – beim Bau der
Website im Ausgabeordner, die Originale im Repo bleiben unverändert.

Welche Bilder? Titel-, Galerie- und Textbilder der Redaktionsbeiträge (inhalte/beitraege/*.json) und die Bilder
der alten Beitragsseiten (seiten/beitrag-*.html, seiten/wandern-*.html).
Bilder, die das Zeichen schon haben, bleiben unverändert. Die Prüfung („hat schon ein Zeichen?“) ist ein
Bildvergleich mit der Logo-Form in der Ecke unten rechts; die Ergebnisse stehen in werkzeuge/schheimat.json
(Schlüssel = Bildpfad + Dateigröße), damit nicht jeder Bau alle Bilder neu prüfen muss. Dort stehen auch Bilder,
die bewusst kein Zeichen bekommen (Grafiken/Banner, Wanderbilder mit Naturpark-Logo in der Ecke): „nicht“.
Redaktionsbeiträge mit „SCHeimat-Zeichen ist schon im Bild“ (ohne_marke) lassen das Titelbild aus.

Aufruf:  python3 werkzeuge/schheimat.py AUSGABEORDNER      (braucht Pillow und numpy)
Abgleich 18.11.2026: von 1145 Bildern hatten 1082 das Zeichen schon, 38 bekamen es neu, 25 bleiben ohne.
"""
import glob
import json
import os
import re
import sys

import numpy as np
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MARKE = os.path.join(REPO, "assets", "sponsorenleiste", "schheimat.webp")
STATUS = os.path.join(REPO, "werkzeuge", "schheimat.json")
MIN_SEITE = 300        # kleinere Bilder bekommen kein Zeichen
SCHWELLE = 0.7         # ab diesem Vergleichswert gilt das Zeichen als vorhanden
BREITE = 0.126         # Breite des Zeichens relativ zur kurzen Bildseite (Mittel der vorhandenen Zeichen)
RECHTS, UNTEN = 0.012, 0.038

_marke = None


def marke():
    global _marke
    if _marke is None:
        m = Image.open(MARKE).convert("RGBA")
        a = np.array(m)[..., 3]
        ys, xs = np.where(a > 20)
        _marke = m.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))
    return _marke


def _ncc(bild, t):
    th, tw = t.shape
    t = t - t.mean()
    tn = np.sqrt((t ** 2).sum())
    H, W = bild.shape
    fh, fw = H + th, W + tw
    kor = np.fft.irfft2(np.fft.rfft2(bild, (fh, fw)) * np.fft.rfft2(t[::-1, ::-1], (fh, fw)), (fh, fw))[th - 1:H, tw - 1:W]
    ii = np.pad(bild, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    ii2 = np.pad(bild ** 2, ((1, 0), (1, 0))).cumsum(0).cumsum(1)
    fen = lambda I: I[th:, tw:] - I[:-th, tw:] - I[th:, :-tw] + I[:-th, :-tw]
    s, s2 = fen(ii), fen(ii2)
    return kor / (np.sqrt(np.maximum(s2 - s * s / (th * tw), 1e-6)) * tn)


def vergleichswert(im):
    """Wie sehr gleicht die Ecke unten rechts dem SCHeimat-Zeichen? (0 … 1)"""
    g = im.convert("L")
    w, h = g.size
    sk = 520 / min(w, h)
    g = g.resize((round(w * sk), round(h * sk)), Image.LANCZOS)
    w, h = g.size
    ecke = np.asarray(g.crop((max(0, w - int(h * 0.75)), int(h * 0.6), w, h)), dtype=float)
    maske = marke().getchannel("A")
    best = -1.0
    for f in np.geomspace(0.08, 0.45, 20):
        tw = max(12, round(520 * f))
        th = max(5, round(tw * maske.height / maske.width))
        if th >= ecke.shape[0] or tw >= ecke.shape[1]:
            continue
        best = max(best, float(_ncc(ecke, np.asarray(maske.resize((tw, th), Image.LANCZOS), dtype=float)).max()))
    return best


def stempeln(im):
    """Schwarzer, weich auslaufender Schleier aus der Ecke unten rechts, darauf das Zeichen."""
    im = im.convert("RGBA")
    w, h = im.size
    k = min(w, h)
    rx, ry = 0.62 * k, 0.46 * k
    yy, xx = np.mgrid[0:h, 0:w]
    d = np.sqrt(((w - xx) / rx) ** 2 + ((h - yy) / ry) ** 2)
    t = np.clip((d - 0.25) / 0.75, 0, 1)
    alpha = 0.9 * (1 - t * t * (3 - 2 * t))  # smoothstep: dunkel in der Ecke, weich auslaufend
    schleier = np.zeros((h, w, 4), dtype=np.uint8)
    schleier[..., 3] = (alpha * 255).astype(np.uint8)
    im.alpha_composite(Image.fromarray(schleier, "RGBA"))
    m = marke()
    mb = round(k * BREITE)
    mh = round(m.height * mb / m.width)
    m = m.resize((mb, mh), Image.LANCZOS)
    im.alpha_composite(m, (w - mb - round(k * RECHTS), h - mh - round(k * UNTEN)))
    return im


def bilder():
    """Bildpfad -> (auslassen, aus_redaktion). auslassen: Titelbild mit „Zeichen ist schon im Bild“."""
    aus = {}

    def dazu(b, auslassen=False, redaktion=False):
        b = (b or "").split("?")[0]
        if b.startswith("../"):
            b = b[3:]
        if b.startswith("assets/") and b.lower().endswith((".webp", ".jpg", ".jpeg", ".png")):
            alt = aus.get(b, (False, False))
            aus[b] = (alt[0] or auslassen, alt[1] or redaktion)

    for f in glob.glob(os.path.join(REPO, "inhalte", "beitraege", "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        dazu(d.get("bild"), bool(d.get("ohne_marke")), True)
        for g in d.get("galerie") or []:
            dazu(g if isinstance(g, str) else (g.get("bild") or g.get("src")), False, True)
        for src in re.findall(r'src="([^"]+)"', d.get("text") or ""):
            dazu(src, False, True)
    for f in glob.glob(os.path.join(REPO, "seiten", "beitrag-*.html")) + glob.glob(os.path.join(REPO, "seiten", "wandern-*.html")):
        t = open(f, encoding="utf-8").read()
        m = re.search(r"<main.*?</main>", t, re.S)
        for src in re.findall(r'<img[^>]+src="([^"]+)"', m.group(0) if m else ""):
            dazu(src)
    return aus


def main(ziel):
    status = json.load(open(STATUS, encoding="utf-8")) if os.path.exists(STATUS) else {}
    neu_geprueft, gesetzt = 0, 0
    fehler = 0
    for b, (auslassen, redaktion) in sorted(bilder().items()):
        quelle = os.path.join(REPO, b)
        if auslassen or not os.path.exists(quelle):
            continue
        try:
            schluessel = f"{b}|{os.path.getsize(quelle)}"
            st = status.get(schluessel)
            if st is None:
                # Neu prüfen nur Bilder aus der Redaktion; unbekannte Bilder alter Seiten (z. B. die Beiträge aus
                # 2025, die nur beim Live-Bau dazukommen) bleiben, wie sie sind
                if not redaktion:
                    continue
                im = Image.open(quelle)
                if min(im.size) < MIN_SEITE:
                    st = "nicht"
                else:
                    st = "hat" if vergleichswert(im) >= SCHWELLE else "setzen"
                status[schluessel] = st
                neu_geprueft += 1
            if st != "setzen":
                continue
            im = Image.open(quelle)
            fmt = (im.format or "WEBP").upper()
            out = stempeln(im)
            pfad = os.path.join(ziel, b)
            os.makedirs(os.path.dirname(pfad), exist_ok=True)
            if fmt == "JPEG":
                out.convert("RGB").save(pfad, "JPEG", quality=90)
            elif fmt == "PNG":
                out.save(pfad, "PNG")
            else:
                out.save(pfad, "WEBP", quality=88, method=6)
            gesetzt += 1
        except Exception as e:  # ein kaputtes Bild darf den Bau nicht abbrechen
            fehler += 1
            print(f"  SCHeimat: {b} übersprungen ({e})")
    if neu_geprueft:
        try:
            json.dump(dict(sorted(status.items())), open(STATUS, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
        except OSError:
            pass
    print(f"SCHeimat: {gesetzt} Bilder mit Zeichen versehen ({neu_geprueft} neu geprüft, {fehler} übersprungen).")


if __name__ == "__main__":
    # Nur in einen Ausgabeordner schreiben – nie in das Repo selbst (die Originale bleiben unverändert)
    if len(sys.argv) < 2 or os.path.realpath(sys.argv[1]) == os.path.realpath(REPO):
        sys.exit("Aufruf: python3 werkzeuge/schheimat.py AUSGABEORDNER (nicht das Repo selbst)")
    main(sys.argv[1])
