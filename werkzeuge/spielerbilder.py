"""Spielerfotos und Rückennummern für die Wechsel-Karten im Liveticker (Spielbericht und seiten/live.html).

Quelle sind die Kaderseiten seiten/erste-mannschaft.html und seiten/zweite-mannschaft.html – dort liegen die
Fotos schon auf unserer Seite (assets/...), es geht also keine Anfrage an FuPa. Wer dort fehlt, bekommt auf der
Karte einen neutralen Platzhalter.
"""
import html
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEITEN = {"m1": "seiten/erste-mannschaft.html", "m2": "seiten/zweite-mannschaft.html"}
_KADER = {}

KARTE = re.compile(r'<div class="sp-spieler">(.*?)<span class="kd-name"><em>(.*?)</em>\s*(.*?)(?:<small|</span>)', re.S)


def kader(team):
    """team -> Liste von {"name", "bild" (Pfad ab Repo-Wurzel oder ""), "nr"}"""
    if team not in _KADER:
        liste = []
        pfad = SEITEN.get(team)
        try:
            text = open(os.path.join(REPO, pfad), encoding="utf-8").read() if pfad else ""
        except OSError:
            text = ""
        for m in KARTE.finditer(text):
            kopf = m.group(1)
            name = html.unescape(f"{m.group(2)} {m.group(3)}").strip()
            bild = re.search(r'<img src="\.\./([^"]+)"', kopf)
            nr = re.search(r"<b>(\d+)</b>", kopf)
            liste.append({"name": name, "bild": bild.group(1) if bild else "", "nr": nr.group(1) if nr else ""})
        _KADER[team] = liste
    return _KADER[team]


def _gleich(a, b):
    a, b = (a or "").lower().strip(), (b or "").lower().strip()
    if not a or not b:
        return False
    if a == b:
        return True
    # „T. Kahlmeyer“, „Kahlmeyer“, „Thomas Kahlmeyer“: Nachname gleich und Vorname passt (oder fehlt)
    aa, bb = a.split(), b.split()
    return aa[-1] == bb[-1] and (len(aa) == 1 or len(bb) == 1 or aa[0][0] == bb[0][0])


def spieler(team, name):
    """Name aus dem Ticker -> {"name", "bild", "nr"}; ohne Treffer nur der Name."""
    for teams in ([team] if team in SEITEN else []) + [t for t in SEITEN if t != team]:
        treffer = [p for p in kader(teams) if _gleich(p["name"], name)]
        if len(treffer) == 1:
            return {"name": name, "bild": treffer[0]["bild"], "nr": treffer[0]["nr"]}
        if team in SEITEN:
            break  # nur im eigenen Kader suchen, wenn die Mannschaft bekannt ist
    return {"name": name, "bild": "", "nr": ""}


def karte_html(team, rein, raus, praefix="../", wappen="assets/logo.png"):
    """Wechsel-Karte wie bei Werder: links eingewechselt (grüner Pfeil), Mitte Wappen, rechts ausgewechselt."""
    e = lambda x: html.escape(x or "", quote=True)

    def seite(p, art):
        foto = (f'<img src="{e(praefix + p["bild"])}" alt="" loading="lazy">' if p["bild"]
                else '<span class="sb-wk-ohne" aria-hidden="true"></span>')
        nr = f'<b class="sb-wk-nr">{e(p["nr"])}</b>' if p["nr"] else ""
        pfeil = f'<span class="sb-wk-pfeil" aria-hidden="true">{"↑" if art == "rein" else "↓"}</span>'
        hinweis = "Eingewechselt" if art == "rein" else "Ausgewechselt"
        return (f'<div class="sb-wk-seite sb-wk-{art}"><span class="sb-wk-foto">{foto}{nr}</span>'
                f'<span class="sb-wk-name"><small class="sb-wk-sr">{hinweis}: </small>{e(p["name"])}</span>{pfeil}</div>')

    teile = [seite(spieler(team, rein), "rein")]
    teile.append(f'<img class="sb-wk-wappen" src="{e(praefix + wappen)}" alt="" aria-hidden="true">')
    if raus:
        teile.append(seite(spieler(team, raus), "raus"))
    return f'<div class="sb-wk{"" if raus else " sb-wk-allein"}">{"".join(teile)}</div>'
