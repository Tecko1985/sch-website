"""Spielerfotos und Rückennummern für die Wechsel-Karten im Liveticker (Spielbericht und seiten/live.html).

Quelle sind die Kaderseiten seiten/erste-mannschaft.html, seiten/zweite-mannschaft.html, seiten/u19.html und seiten/u17.html – dort liegen die
Fotos schon auf unserer Seite (assets/...), es geht also keine Anfrage an FuPa. Wer dort fehlt, bekommt auf der
Karte einen neutralen Platzhalter.
"""
import html
import json
import os
import re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEITEN = {"m1": "seiten/erste-mannschaft.html", "m2": "seiten/zweite-mannschaft.html", "u19": "seiten/u19.html",
          "u17-1": "seiten/u17.html", "u17-2": "seiten/u17.html"}   # B1 und B2 stehen beide auf der U17-Seite
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


def _norm(name):
    return " ".join((name or "").lower().replace("-", " ").split())


def _gleich(a, b):
    """Gleicher Spieler? Genau gleich, oder Nachname gleich und Vorname nur abgekürzt bzw. fehlend
    („T. Kahlmeyer“, „Kahlmeyer“). Zwei ausgeschriebene, verschiedene Vornamen (Adam/Alexander) zählen nicht."""
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return False
    if a == b:
        return True
    aa, bb = a.split(), b.split()
    if aa[-1] != bb[-1]:
        return False
    if len(aa) == 1 or len(bb) == 1:
        return True
    va, vb = aa[0].rstrip("."), bb[0].rstrip(".")
    kurz = len(va) == 1 or len(vb) == 1
    return va == vb or (kurz and va[0] == vb[0])


_FUPA = None


def fupa_fotos(team):
    """Fotos aus werkzeuge/spielerfotos.json (FuPa-Kader von 1., 2. und U19, geholt mit spielerfotos.py)."""
    global _FUPA
    if _FUPA is None:
        try:
            _FUPA = json.load(open(os.path.join(REPO, "werkzeuge", "spielerfotos.json"), encoding="utf-8"))
        except (OSError, ValueError):
            _FUPA = {}
    return _FUPA.get(team, [])


# Mannschaften, für die es Karten mit Namen und Foto gibt. Datenschutz (Minderjährige): beim Nachwuchs wie bei
# den Torschützen auf den automatischen Seiten (spielvorschau.NAMEN_TEAMS) nur ab der U17 (U19, U17, U16).
KARTEN_TEAMS = {"m1": "m1", "m2": "m2", "u19-1": "u19", "u19": "u19", "u17-1": "u17-1", "u17-2": "u17-2"}
ALLE_TEAMS = ("m1", "m2", "u19", "u17-1", "u17-2")


def karten_team(kuerzel):
    """Mannschaftskürzel (m1, m2, u19-1, u17-1 …) -> Schlüssel für die Fotosuche, oder None (keine Karten)."""
    return KARTEN_TEAMS.get(kuerzel)


def _quellen(team):
    """Suchreihenfolge: erst alle unsere Kaderseiten (dort liegen die aktuellen Saisonfotos), eigene Mannschaft
    zuerst, dann die anderen Herren, dann die U19 – erst danach die FuPa-Listen als Ersatz. So bekommt z. B. ein
    Spieler der Ersten, der in der Zweiten aushilft, sein neues Foto von der Kaderseite der Ersten statt eines
    älteren FuPa-Bilds aus dem Kader der Zweiten (Abgleich 17.11.2026)."""
    reihe = [team] + [t for t in ALLE_TEAMS if t != team]
    for t in reihe:
        if t in SEITEN:
            yield t, kader(t)
    for t in reihe:
        yield t, fupa_fotos(t)


def spieler(team, name):
    """Name aus dem Ticker -> {"name", "bild", "nr"}; ohne Treffer nur der Name.
    Erst der genaue Name in allen Kadern, dann Kurzformen („T. Kahlmeyer“) – die nur, wenn eindeutig.
    Die Rückennummer nur aus der eigenen Mannschaft (in der U19 oder Ersten trägt er oft eine andere)."""
    quellen = list(_quellen(team))
    eigene = [l for t, l in quellen if t == team]
    for pruef in (lambda p: _norm(p["name"]) == _norm(name), lambda p: _gleich(p["name"], name)):
        for t, liste in quellen:
            treffer = [p for p in liste if p["bild"] and pruef(p)]
            if len({_norm(p["name"]) for p in treffer}) == 1:
                voll = _norm(treffer[0]["name"])
                nr = next((x["nr"] for l in eigene for x in l if _norm(x["name"]) == voll and x["nr"]), "")
                return {"name": name, "bild": treffer[0]["bild"], "nr": nr}
    return {"name": name, "bild": "", "nr": ""}


BALL_SVG = ('<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="10.5" fill="#fff" stroke="currentColor" stroke-width="1.6"/>'
            '<path d="M12 7.2l4.1 3-1.6 4.8h-5l-1.6-4.8z" fill="currentColor"/><path d="M12 1.6v5.6M16.1 10.2l5-1.8M14.5 15l3.2 4.4'
            'M9.5 15l-3.2 4.4M7.9 10.2l-5-1.8" stroke="currentColor" stroke-width="1.4" fill="none"/></svg>')


def _seite(p, art, praefix, zeile2=""):
    e = lambda x: html.escape(x or "", quote=True)
    foto = (f'<img src="{e(praefix + p["bild"])}" alt="" loading="lazy">' if p["bild"]
            else '<span class="sb-wk-ohne" aria-hidden="true"></span>')
    nr = f'<b class="sb-wk-nr">{e(p["nr"])}</b>' if p["nr"] else ""
    zeichen = {"rein": "↑", "raus": "↓", "tor": BALL_SVG}[art]
    hinweis = {"rein": "Eingewechselt", "raus": "Ausgewechselt", "tor": "Torschütze"}[art]
    unter = f'<small class="sb-wk-zusatz">{e(zeile2)}</small>' if zeile2 else ""
    return (f'<div class="sb-wk-seite sb-wk-{art}"><span class="sb-wk-foto">{foto}{nr}</span>'
            f'<span class="sb-wk-name"><small class="sb-wk-sr">{hinweis}: </small>{e(p["name"])}{unter}</span>'
            f'<span class="sb-wk-pfeil" aria-hidden="true">{zeichen}</span></div>')


def _wappen(praefix, wappen):
    return f'<img class="sb-wk-wappen" src="{html.escape(praefix + wappen, quote=True)}" alt="" aria-hidden="true">'


def karte_html(team, rein, raus, praefix="../", wappen="assets/logo.png"):
    """Wechsel-Karte wie bei Werder: links eingewechselt (grüner Pfeil), Mitte Wappen, rechts ausgewechselt."""
    teile = [_seite(spieler(team, rein), "rein", praefix), _wappen(praefix, wappen)]
    if raus:
        teile.append(_seite(spieler(team, raus), "raus", praefix))
    return f'<div class="sb-wk{"" if raus else " sb-wk-allein"}">{"".join(teile)}</div>'


def torkarte_html(team, schuetze, vorlage="", zusatz="", praefix="../", wappen="assets/logo.png"):
    """Tor-Karte: Torschütze mit Foto und Nummer, darunter Vorlage bzw. Strafstoß/Kopfball, Ball, Wappen."""
    unter = f"Vorlage: {vorlage}" if vorlage else zusatz
    return (f'<div class="sb-wk sb-wk-allein sb-tk">{_seite(spieler(team, schuetze), "tor", praefix, unter)}'
            f'{_wappen(praefix, wappen)}</div>')
