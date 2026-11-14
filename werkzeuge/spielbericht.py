"""Spielbericht-Seite im Aufbau von spielbericht-erfurt.html für Redaktionsbeiträge der Rubrik „Spielbericht“.

Wird von werkzeuge/beitraege.py benutzt. Eingaben kommen aus dem Beitrags-JSON:
- die üblichen Felder (titel, datum, teaser, bild, text, galerie)
- "spiel": Spieldaten aus der Redaktion (Gegner, Ergebnis, Tore, Aufstellung, Ticker, Stimmen, Vorbericht …)

Reiter: Vorbericht, Spielinfo, Spielbericht, Galerie, Liveticker, Stimmen, Statistiken, Aufstellung.
Reiter ohne Inhalt fallen weg. Alle Pfade werden hier vom Hauptordner aus geschrieben und erst
am Ende für seiten/ umgeschrieben.
"""
import html
import json
import os
import re

SCH = "1. SC 1911 Heiligenstadt"
SCH_WAPPEN = "sch-startseite/assets/logo.png"
LEER_WAPPEN = "assets/wappen-leer.svg"
TAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
BILDPFAD = re.compile(r"^assets/beitraege/[a-z0-9._-]+$")

BALL = ('<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.4"/>'
        '<path d="m8 4.5 3 2.2-1.2 3.6H6.2L5 6.7z" fill="currentColor"/></svg>')
POKAL = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 4h10v4a5 5 0 0 1-10 0V4Zm0 2H4a3 3 0 0 0 3 4m10-4h3a3 3 0 0 1-3 4M12 13v4m-4 3h8m-6-3h4"/></svg>')


def e(s):
    return html.escape(str(s or ""), quote=True)


def zeilen(t):
    return [z.strip() for z in str(t or "").replace("\r", "").split("\n") if z.strip()]


def platzhalter(t):
    return bool(re.search(r"\[[^\]]{1,80}\]", t or ""))


def zahl(t):
    t = str(t if t is not None else "").strip()
    return int(t) if t.isdigit() else None


# ---------------------------------------------------------------- Spieldaten lesen
def minute(zeile):
    """„13. Fehler (Strafstoß)“ / „90+2' Name“ -> (sortierwert, „13“ / „90+2“, Rest)"""
    m = re.match(r"^\s*(\d{1,3})\s*(?:\+\s*(\d{1,2}))?\s*[.'’´]?\s*(.*)$", zeile)
    if not m:
        return None
    n, plus, rest = int(m.group(1)), m.group(2), m.group(3).strip(" -–:")
    return n + (int(plus) / 100 if plus else 0), f"{n}+{plus}" if plus else str(n), rest


def name_zusatz(rest):
    m = re.match(r"^(.*?)\s*\((.*?)\)\s*$", rest)
    return (m.group(1).strip(), m.group(2).strip()) if m else (rest.strip(), "")


ARTEN = {"FE": "Strafstoß", "ET": "Eigentor", "HE": "Handelfmeter"}
VEREINSFORMAT = re.compile(r"^\s*\d+\s*:\s*\d+\s+(.+?)\s*\(\s*(\d{1,3})(?:\s*\+\s*(\d{1,2}))?\s*\.?\s*([^)]*)\)\s*$")


def vereinsformat(z):
    """„1:0 Wolanski (39. FE)“ -> „39. Wolanski (Strafstoß)“; sonst unverändert."""
    m = VEREINSFORMAT.match(z)
    if not m:
        return z
    name, n, plus, art = m.group(1).strip(), m.group(2), m.group(3), m.group(4).strip().rstrip(".")
    art = ARTEN.get(art.upper(), art)
    return f"{n}{'+' + plus if plus else ''}. {name}" + (f" ({art})" if art else "")


def ereignisse(text, team):
    aus = []
    # Mehrere Einträge in einer Zeile („1:0 A (17.), 2:0 B (30.)“) auftrennen
    teile = [t for z in zeilen(text) for t in re.split(r"\s*[,;]\s*(?![^()]*\))", z) if t.strip()]
    for z in teile:
        m = minute(vereinsformat(z))
        if m and m[2]:
            name, zusatz = name_zusatz(m[2])
            aus.append({"min": m[0], "label": m[1], "name": name, "zusatz": zusatz, "team": team})
    return aus


def aufstellung(text):
    t = str(text or "").strip().strip("[]")
    if not t:
        return []
    teile = re.split(r"\s*\n\s*|\s+[–—-]\s+|\s*;\s*|\s*,\s*(?![^()]*\))", t)
    spieler = []
    for teil in teile:
        teil = teil.strip()
        if not teil:
            continue
        name, wechsel = name_zusatz(teil)
        spieler.append({"name": name, "wechsel": wechsel, "roh": teil})
    return spieler


REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FUELLWOERTER = {"fc", "sv", "tsv", "fsv", "sg", "bsv", "jfc", "jsg", "spvgg", "sc", "vfb", "vfl", "ssv", "jfv", "e.v.", "1."}


def _worte(name):
    return {w for w in re.split(r"[\s/\-.]+", (name or "").lower()) if len(w) > 2 and w not in FUELLWOERTER and not w.isdigit()}


def wappen_fuer(gegner):
    """Passendes Vereinswappen aus assets/wappen/wappen.json (von werkzeuge/spiele.py gefüllt)."""
    try:
        namen = json.load(open(os.path.join(REPO, "assets/wappen/wappen.json"), encoding="utf-8"))
    except (OSError, ValueError):
        return None
    gesucht = _worte(gegner)
    if not gesucht:
        return None
    bester, punkte = None, 0
    for name, datei in namen.items():
        w = _worte(name)
        treffer = len(w & gesucht)
        # mehr gemeinsame Wörter gewinnt; bei Gleichstand der Name mit weniger fremden Wörtern
        wert = treffer * 10 - len(w - gesucht)
        if treffer and wert > punkte and os.path.exists(os.path.join(REPO, "assets/wappen", datei)):
            bester, punkte = datei, wert
    return f"assets/wappen/{bester}" if bester else None


class Spiel:
    def __init__(self, sp, d):
        self.sp = sp
        self.gegner = (sp.get("gegner") or "").strip()
        self.da = bool(self.gegner)
        self.heim = sp.get("ort_art", "heim") != "auswaerts"
        self.tore = sorted(ereignisse(sp.get("tore_sch"), "sch") + ereignisse(sp.get("tore_geg"), "geg"), key=lambda x: x["min"])
        self.tore = self.teams_aus_spielstand(sp) or self.tore
        self.karten = sorted(ereignisse(sp.get("karten_sch"), "sch") + ereignisse(sp.get("karten_geg"), "geg"), key=lambda x: x["min"])
        self.elf_sch = aufstellung(sp.get("aufstellung_sch"))
        self.elf_geg = aufstellung(sp.get("aufstellung_geg"))
        # Endstand: eingetragen oder aus den Torschützen gezählt
        es, eg = zahl(sp.get("end_sch")), zahl(sp.get("end_geg"))
        if es is None and eg is None and self.tore:
            es, eg = self.zaehle(999)
        hs, hg = zahl(sp.get("hz_sch")), zahl(sp.get("hz_geg"))
        if hs is None and hg is None and self.tore:
            hs, hg = self.zaehle(45.99)
        self.end = (es, eg) if es is not None and eg is not None else None
        self.hz = (hs, hg) if hs is not None and hg is not None else None
        self.spieldatum = sp.get("spieldatum") or d["datum"]
        # Eigenes Wappen aus der Redaktion, sonst das Vereinswappen aus assets/wappen/ (über den Namen), sonst neutral
        self.wappen = (sp.get("wappen") if BILDPFAD.match(sp.get("wappen") or "") else None) or wappen_fuer(self.gegner) or LEER_WAPPEN

    def teams_aus_spielstand(self, sp):
        """Stehen alle Tore im Vereinsformat („1:1 Kurth (31.)“) da, ergibt der Spielstand,
        wer getroffen hat – auch wenn beide Mannschaften in einem Feld stehen."""
        roh = [t for f in ("tore_sch", "tore_geg") for z in zeilen(sp.get(f))
               for t in re.split(r"\s*[,;]\s*(?![^()]*\))", z) if t.strip()]
        if not roh or not all(VEREINSFORMAT.match(t) for t in roh):
            return None
        aus, vor = [], (0, 0)
        for t in sorted(roh, key=lambda t: sum(int(x) for x in re.match(r"\s*(\d+)\s*:\s*(\d+)", t).groups())):
            h, g = (int(x) for x in re.match(r"\s*(\d+)\s*:\s*(\d+)", t).groups())
            heim_tor = h > vor[0]
            vor = (h, g)
            for ev in ereignisse(t, "sch" if heim_tor == self.heim else "geg"):
                aus.append(ev)
        return sorted(aus, key=lambda x: x["min"])

    def zaehle(self, bis):
        s = sum(1 for t in self.tore if t["team"] == "sch" and t["min"] <= bis)
        g = sum(1 for t in self.tore if t["team"] == "geg" and t["min"] <= bis)
        return s, g

    # heim/gast-Reihenfolge
    def hg(self, paar):
        return paar if self.heim else (paar[1], paar[0])

    def stand(self, paar):
        h, g = self.hg(paar)
        return f"{h} : {g}"

    def teams(self):
        a = (SCH, SCH_WAPPEN, self.elf_sch)
        b = (self.gegner, self.wappen, self.elf_geg)
        return (a, b) if self.heim else (b, a)

    def kurzname(self, team):
        return "SCH" if team == "sch" else self.gegner


def datum_lang(iso):
    j, m, t = iso.split("-")
    return f"{t}. {MONATE[int(m) - 1]} {j}"


def datum_tag(iso):
    import datetime
    j, m, t = (int(x) for x in iso.split("-"))
    return f"{TAGE[datetime.date(j, m, t).weekday()]}, {t:02d}.{m:02d}.{j}"


# ---------------------------------------------------------------- Bausteine
def tafel(s):
    if not s.da:
        return ""
    sp = s.sp
    (n1, w1, _), (n2, w2, _) = s.teams()
    oben = e(sp.get("wettbewerb") or "Spiel")
    zweite = ", ".join(e(x) for x in (sp.get("runde"), sp.get("spielort")) if x)
    zeit = datum_tag(s.spieldatum) + (f" | {e(sp.get('anstoss'))} Uhr" if sp.get("anstoss") else "")
    stand = (f'<strong aria-label="Endstand {s.hg(s.end)[0]} zu {s.hg(s.end)[1]}">{s.stand(s.end)}</strong>' if s.end
             else '<strong>– : –</strong>')
    hz = f"<span>Halbzeit {s.stand(s.hz)}</span>" if s.hz else ""
    # Vereinsformat mit Spielstand: „1:0 Wolanski (39. FE)“
    kurz = {v: k for k, v in ARTEN.items()}
    lauf, tore = [0, 0], ""
    for t in s.tore:
        lauf[0 if t["team"] == "sch" else 1] += 1
        h, g = s.hg(lauf)
        zus = kurz.get(t["zusatz"], t["zusatz"])
        tore += f'<li>{BALL}<span>{h}:{g} {e(t["name"])} ({e(t["label"])}.{" " + e(zus) if zus else ""})</span></li>'
    tore += "".join(f'<li class="rot"><span class="sb-karte" aria-hidden="true"></span><span>{e(k["label"])}. Rote Karte {e(k["name"])}</span></li>' for k in s.karten)
    tore_html = f'\n<ul class="sb-tore" aria-label="Tore und Platzverweise">{tore}</ul>' if tore else ""
    return f"""<section class="sb-tafel" aria-label="Ergebnis">
<div class="sb-tafel-innen">
<div class="sb-meta"><span class="sb-meta-icon">{POKAL}</span><p><b>{oben}</b>{zweite}{"<br>" if zweite else ""}{zeit}</p></div>
<div class="sb-paar"><span class="sb-team stitel">{e(n1)}</span><img class="sb-wappen" src="{w1}" alt=""><div class="sb-stand">{stand}{hz}</div><img class="sb-wappen" src="{w2}" alt=""><span class="sb-team stitel">{e(n2)}</span></div>
<span class="sb-status">{"Beendet" if s.end else "Spielbericht"}</span>{tore_html}
</div>
</section>"""


def figur(pfad, unterschrift=""):
    cap = f"<figcaption>{e(unterschrift)}</figcaption>" if unterschrift else ""
    return f'<figure><img src="{pfad}" alt="" loading="lazy">{cap}</figure>'


def nur_text(t):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()


def ist_kicker(inner):
    t = nur_text(inner)
    return "<br>" not in inner and 0 < len(t) <= 40 and not re.search(r"[.!?:,;“”\"]$", t)


def text_abschnitte(text):
    """Gesäuberten Beitragstext in Abschnitte im Spielbericht-Stil umbauen.
    h2 oder eine kurze Einzelzeile = kleine Rubrik (Kicker), h3 oder die erste Zeile eines Absatzes
    vor einem Zeilenumbruch = Zwischenüberschrift."""
    bloecke = re.findall(r"<(p|h2|h3|ul|ol|blockquote)>(.*?)</\1>", text or "", re.S)
    abschnitte, kicker, aktuell = [], None, None

    def neu(h3=""):
        nonlocal kicker, aktuell
        aktuell = {"kicker": kicker, "h3": h3, "teile": []}
        abschnitte.append(aktuell)
        kicker = None

    def absaetze(inner):
        return "".join(f"<p>{x.strip()}</p>" for x in re.split(r"<br>", inner) if nur_text(x))

    for tag, inner in bloecke:
        if tag == "h2" or (tag == "p" and ist_kicker(inner)):
            kicker = nur_text(inner)
            aktuell = None
            continue
        if tag == "h3":
            neu(nur_text(inner))
            continue
        if tag == "p" and "<br>" in inner:
            kopf, rest = inner.split("<br>", 1)
            k = nur_text(kopf)
            if 0 < len(k) <= 110 and not re.search(r"[.!?:,;“”\"]$|[\[:]", k) and nur_text(rest):
                neu(k)
                aktuell["teile"].append(absaetze(rest))
                continue
        if aktuell is None or kicker:
            neu()
        if tag == "p":
            aktuell["teile"].append(absaetze(inner))
        elif tag == "blockquote":
            innen = inner if inner.lstrip().startswith("<p>") else f"<p>{inner}</p>"
            aktuell["teile"].append(f'<blockquote class="sb-zitat">{innen}</blockquote>')
        else:
            aktuell["teile"].append(f"<{tag}>{inner}</{tag}>")
    if kicker:
        neu()

    aus = []
    for a in abschnitte:
        if not a["teile"] and not a["h3"]:
            continue
        kl = "sb-abschnitt" if a["kicker"] else "sb-weiter"
        k = f'<span class="sb-kicker">{e(a["kicker"])}</span>' if a["kicker"] else ""
        h = f'<h3 class="stitel">{e(a["h3"])}</h3>' if a["h3"] else ""
        aus.append(f'<section class="{kl}">{k}{h}{"".join(a["teile"])}</section>')
    return aus


def verteile(teile, bilder, unterschrift):
    """Bilder gleichmäßig zwischen die Abschnitte setzen (nie vor den ersten Abschnitt)."""
    if not bilder:
        return teile
    n = len(teile)
    if n == 0:
        return [figur(b, unterschrift) for b in bilder]
    k = len(bilder)
    # Abschnitt, nach dem Bild i kommt: gleichmäßig über den Text verteilt
    nach = [max(1, min(n, round((i + 1) * n / (k + 1)))) for i in range(k)]
    aus = []
    for j, teil in enumerate(teile, 1):
        aus.append(teil)
        aus += [figur(b, unterschrift) for b, pos in zip(bilder, nach) if pos == j]
    return aus


def artikel(titel, datum, autor, vorspann, text, bilder, unterschrift, schluss="", oben_bild="", kicker=""):
    """bilder: kommen zwischen die Abschnitte; oben_bild: steht direkt unter der Überschrift."""
    teile = verteile(text_abschnitte(text), bilder, unterschrift)
    zeile = datum_lang(datum) + (f" · {e(autor)}" if autor else "")
    oben = figur(oben_bild, unterschrift).replace(' loading="lazy"', "") if oben_bild else ""
    kk = f'<span class="sb-kicker">{e(kicker)}</span>\n' if kicker else ""
    vs = f'<p class="sb-vorspann">{e(vorspann)}</p>' if vorspann else ""
    return (f'<article class="sb-artikel">\n{kk}<h2 class="stitel">{e(titel)}</h2>\n<p class="sb-autor">{zeile}</p>\n'
            f'{oben}\n{vs}\n{"".join(teile)}\n{schluss}</article>')


def spieldaten(s):
    if not s.da:
        return ""
    zeilen_ = []
    for name, elf in ((SCH, s.elf_sch), (s.gegner, s.elf_geg)):
        if elf:
            zeilen_.append(f'<p><b>{e(name)}:</b> {" – ".join(e(x["roh"]) for x in elf)}</p>')
    if s.tore:
        lauf, liste = [0, 0], []
        for t in s.tore:
            lauf[0 if t["team"] == "sch" else 1] += 1
            h, g = s.hg(lauf)
            zus = f', {e(t["zusatz"])}' if t["zusatz"] else ""
            liste.append(f'{h}:{g} {e(t["name"])} ({e(t["label"])}.{zus})')
        zeilen_.append(f"<p><b>Tore:</b> {', '.join(liste)}</p>")
    if s.karten:
        k = ", ".join(f'{e(x["name"])} ({e(x["label"])}.{", " + e(x["zusatz"]) if x["zusatz"] else ""})' for x in s.karten)
        zeilen_.append(f"<p><b>Rote Karte:</b> {k}</p>")
    for feld, text in (("schiedsrichter", "Schiedsrichter"), ("zuschauer", "Zuschauer"), ("trainer", "Trainer")):
        if s.sp.get(feld):
            zeilen_.append(f"<p><b>{text}:</b> {e(s.sp[feld])}</p>")
    if not zeilen_:
        return ""
    return '<section class="sb-daten">\n<h3 class="stitel">Spieldaten</h3>\n' + "\n".join(zeilen_) + "\n</section>\n"


def spielinfo(s):
    if not s.da:
        return ""
    sp = s.sp
    felder = [("Wettbewerb", sp.get("wettbewerb")), ("Runde", sp.get("runde")),
              ("Anstoß", datum_tag(s.spieldatum) + (f", {sp['anstoss']} Uhr" if sp.get("anstoss") else "")),
              ("Spielort", sp.get("spielort")), ("Zuschauer", sp.get("zuschauer")), ("Schiedsrichter", sp.get("schiedsrichter")),
              ("Endstand", s.stand(s.end) if s.end else ""), ("Halbzeit", s.stand(s.hz) if s.hz else "")]
    dl = "\n".join(f"<div><dt>{a}</dt><dd>{e(b)}</dd></div>" for a, b in felder if b)
    links = ['<a href="#spielbericht" data-sb-zu="spielbericht">Zum Spielbericht</a>']
    if s.elf_sch or s.elf_geg:
        links.append('<a href="#aufstellung" data-sb-zu="aufstellung">Zu den Aufstellungen</a>')
    return (f'<div class="sb-schmal">\n<h2 class="sb-h2 stitel">Spielinfo</h2>\n<dl class="sb-info">\n{dl}\n</dl>\n'
            f'<p class="sb-hinweis">{" · ".join(links)}</p>\n</div>')


def galerie(bilder, titel):
    if not bilder:
        return ""
    knoepfe = "".join(f'<button type="button" data-gross="{b}"><img src="{b}" alt="{e(titel)}, Bild {i}" loading="lazy"></button>'
                      for i, b in enumerate(bilder, 1))
    return f'<h2 class="sb-h2 stitel">Das Spiel in Bildern</h2>\n<div class="sb-galerie">{knoepfe}</div>'


FUPA_KLASSE = {"tor": "tor", "pfiff": "pfiff", "wechsel": "wechsel", "karte": "karte", "gelb": "karte"}
FUPA_ZEICHEN = {"wechsel": '<span class="sb-wechsel" aria-hidden="true">⇄</span> ',
                "karte": '<span class="sb-karte" aria-hidden="true"></span>',
                "gelb": '<span class="sb-karte gelb" aria-hidden="true"></span>'}
_FUPA_SPIELE = {}


def fupa_eintraege(s):
    """FuPa-Ticker zum Spiel: über den Ticker-Link aus der Redaktion, sonst über Datum und Gegner
    in den Spielen der 1. und 2. Mannschaft. Ohne Netz oder ohne Treffer: leere Liste."""
    try:
        import fupa_ticker
    except ImportError:
        return [], ""
    slug = fupa_ticker.slug_aus_link(s.sp.get("ticker_link"))
    try:
        if not slug and s.da:
            worte = [w for w in _worte(s.gegner) if len(w) > 3] or list(_worte(s.gegner))
            j, mo = int(s.spieldatum[:4]), int(s.spieldatum[5:7])
            saison = f"{j}-{str(j + 1)[2:]}" if mo >= 7 else f"{j - 1}-{str(j)[2:]}"
            for team in ("m1", "m2"):
                schluessel = f"{team}-{saison}"
                if schluessel not in _FUPA_SPIELE:
                    _FUPA_SPIELE[schluessel] = fupa_ticker.hole_json(
                        f"{fupa_ticker.API}/v1/teams/1-sc-1911-heiligenstadt-{schluessel}/matches?flavor=past&limit=40")
                m = fupa_ticker.finde_spiel(_FUPA_SPIELE[schluessel], s.spieldatum, worte)
                if m:
                    slug = m["slug"]
                    break
        if not slug:
            return [], ""
        return fupa_ticker.ereignisse(fupa_ticker.stream(slug)), f"https://www.fupa.net/match/{slug}"
    except Exception as fehler:  # FuPa nicht erreichbar: Ticker aus den Spieldaten
        print(f"  FuPa-Ticker nicht geladen ({fehler})")
        return [], ""


def ticker(s, fazit):
    sp = s.sp
    link = (sp.get("ticker_link") or "").strip()
    if not re.match(r"^https?://", link):
        link = ""
    if not s.da and not link:
        return ""
    eintraege = []  # (min, klasse, überschrift, text, stand)

    def stand_bei(mn):
        h, g = s.hg(s.zaehle(mn))
        return f"{h}:{g}"

    eigene = []
    for z in zeilen(sp.get("ticker")):
        teile = [x.strip() for x in z.split("|")]
        m = minute(teile[0] + " x")
        if not m or len(teile) < 2:
            continue
        kopf, text = teile[1], " | ".join(teile[2:])
        kl = "tor" if re.match(r"^tor\b", kopf, re.I) else ""
        eigene.append((m[0], m[1], kl, e(kopf), e(text), stand_bei(m[0]) if s.da else ""))
    fupa, fupa_link = ([], "") if eigene else fupa_eintraege(s)
    if eigene:
        eintraege = eigene
        quelle = "Spielverlauf aus der Redaktion."
    elif fupa:
        eintraege = [(x["sort"], x["min"], FUPA_KLASSE.get(x["art"], ""), FUPA_ZEICHEN.get(x["art"], "") + e(x["kopf"]),
                      e(x["text"]), x["stand"]) for x in fupa]
        quelle = "Liveticker von FuPa."
        link = link or fupa_link
    elif s.da:
        quelle = "Spielverlauf aus den Spieldaten des Spielberichts."
        eintraege.append((1, "1", "", "Anpfiff", "Der Ball rollt" + (f" – {e(sp['spielort'])}." if sp.get("spielort") else "."), "0:0"))
        for t in s.tore:
            wer = s.kurzname(t["team"])
            zus = f' ({e(t["zusatz"])})' if t["zusatz"] else ""
            eintraege.append((t["min"], t["label"], "tor", f"Tor für {e(wer)}", f'{e(t["name"])} trifft{zus}.', stand_bei(t["min"])))
        for k in s.karten:
            zus = f' ({e(k["zusatz"])})' if k["zusatz"] else ""
            eintraege.append((k["min"] + 0.001, k["label"], "", f'<span class="sb-karte" aria-hidden="true"></span>Rote Karte für {e(k["name"])}',
                              f"Platzverweis{zus}.", ""))
        # Wechsel aus den Aufstellungen: „Wolanski (73. Opfermann)“ -> 73' Opfermann kommt für Wolanski
        for team, elf in (("sch", s.elf_sch), ("geg", s.elf_geg)):
            for x in elf:
                m = minute(x["wechsel"]) if x["wechsel"] else None
                if m and m[2]:
                    eintraege.append((m[0] + 0.002, m[1], "wechsel", f'<span class="sb-wechsel" aria-hidden="true">⇄</span> Wechsel bei {e(s.kurzname(team))}',
                                      f'{e(m[2])} kommt für {e(x["name"])}.', ""))
        if s.hz:
            eintraege.append((45.5, "45", "", "Halbzeit", "Pause.", s.stand(s.hz).replace(" ", "")))
        if s.end:
            eintraege.append((99, "90", "", "Abpfiff", "Das Spiel ist aus.", s.stand(s.end).replace(" ", "")))
    else:
        quelle = ""
    eintraege.sort(key=lambda x: x[0], reverse=True)
    li = "".join(f'<li class="{kl}"><span class="sb-minute">{lab}\'</span><div>'
                 + (f'<h3 class="stitel">{kopf}</h3>' if kopf else "") + (f"<p>{text}</p>" if text else "")
                 + f'</div><span class="stand">{st}</span></li>' for _, lab, kl, kopf, text, st in eintraege)
    kopf = (f'<div class="sb-tickerkopf"><b>Abpfiff</b><span>Endstand {s.stand(s.end)}</span></div>' if s.end
            else '<div class="sb-tickerkopf"><b>Liveticker</b><span></span></div>')
    fz = f'<p class="sb-tickerfazit">{e(fazit)}</p>' if fazit else ""
    q = quelle + (f' <a href="{e(link)}" rel="noopener">Vollständiger Liveticker</a>' if link else "")
    liste = f'<ol class="sb-ereignisse">{li}</ol>' if li else ""
    return f'<div class="sb-ticker">\n{kopf}\n{fz}\n{liste}\n<p class="sb-quelle">{q.strip()}</p>\n</div>'


def stimmen(s):
    aus = []
    for z in zeilen(s.sp.get("stimmen")):
        teile = [x.strip() for x in z.split("|")]
        if len(teile) >= 3:
            name, rolle, zitat = teile[0], teile[1], " | ".join(teile[2:])
        elif len(teile) == 2:
            name, rolle, zitat = teile[0], "", teile[1]
        else:
            name, rolle, zitat = "", "", teile[0]
        zitat = zitat.strip("„“\"")
        if not zitat:
            continue
        fuss = f"<footer><b>{e(name)}</b>{f'<span>{e(rolle)}</span>' if rolle else ''}</footer>" if name else ""
        aus.append(f'<blockquote class="sb-stimme"><p>„{e(zitat)}“</p>{fuss}</blockquote>')
    if not aus:
        return ""
    return '<h2 class="sb-h2 stitel sb-schmal">Stimmen zum Spiel</h2>\n' + '\n'.join(aus)


def statistik(s):
    if not s.da or not s.end:
        return ""
    (n1, w1, _), (n2, w2, _) = s.teams()

    def wechsel(elf):
        return sum(1 for x in elf if x["wechsel"])

    karten = (sum(1 for k in s.karten if k["team"] == "sch"), sum(1 for k in s.karten if k["team"] == "geg"))
    werte = [("Tore", s.end)]
    if s.hz:
        werte += [("Tore 1. Halbzeit", s.hz), ("Tore 2. Halbzeit", (s.end[0] - s.hz[0], s.end[1] - s.hz[1]))]
    werte.append(("Rote Karten", karten))
    if s.elf_sch or s.elf_geg:
        werte.append(("Auswechslungen", (wechsel(s.elf_sch), wechsel(s.elf_geg))))
    dl = ""
    for name, paar in werte:
        a, b = s.hg(paar)
        dl += (f'<dl class="sb-stat" data-a="{a}" data-b="{b}"><dt>{name}</dt><dd class="wert">{a}</dd><dd class="sb-balken links"><i></i></dd>'
               f'<dd class="sb-balken rechts"><i></i></dd><dd class="wert rechts">{b}</dd></dl>')
    return (f'<div class="sb-statkopf"><div><img src="{w1}" alt="">{e(n1)}</div><div>{e(n2)}<img src="{w2}" alt=""></div></div>\n'
            f'<div class="sb-statliste"><h3 class="stitel">Allgemein</h3>{dl}</div>\n'
            '<p class="sb-stathinweis">Quelle: Spieldaten des Spielberichts. Weitere Werte wie Ballbesitz oder Torschüsse liegen für dieses Spiel nicht vor.</p>')


def elf_html(name, wappen, elf, karten):
    li = ""
    for x in elf:
        rot = [k for k in karten if k["name"] and (k["name"] in x["name"] or x["name"] in k["name"])]
        klein = ""
        if rot:
            klein = f'<span class="sb-karte" aria-label="Rote Karte"></span>{e(rot[0]["label"])}.'
        elif x["wechsel"]:
            klein = f'<span class="sb-wechsel">⇄</span> {e(x["wechsel"])}'
        li += f"<li><span>{e(x['name'])}</span><small>{klein}</small></li>"
    return (f'<section class="sb-elf"><header><img src="{wappen}" alt=""><h3 class="stitel">{e(name)}</h3></header>'
            f"<ol>{li}</ol></section>")


def aufstellungen(s):
    if not s.da or not (s.elf_sch or s.elf_geg):
        return ""
    (n1, w1, e1), (n2, w2, e2) = s.teams()
    k1 = [k for k in s.karten if (k["team"] == "sch") == s.heim]
    k2 = [k for k in s.karten if (k["team"] == "sch") != s.heim]
    bloecke = "\n".join(elf_html(n, w, el, k) for n, w, el, k in ((n1, w1, e1, k1), (n2, w2, e2, k2)) if el)
    return (f'<h2 class="sb-h2 stitel">Aufstellungen</h2>\n<div class="sb-aufstellung">\n{bloecke}\n</div>\n'
            '<p class="sb-hinweis">Startelf in der Reihenfolge des Spielberichts, rechts die Wechsel mit Minute.</p>')


def vorbericht_html(vb):
    if not vb:
        return ""
    vorspann = vb["teaser"] if vb.get("teaser") and not platzhalter(vb["teaser"]) else ""
    if vorspann and vorspann.rstrip(" …")[:60] in nur_text(vb["text"])[:800]:
        vorspann = ""  # Anreißer steht schon (fast) wörtlich am Textanfang
    schluss = f'<p class="sb-hinweis"><a href="seiten/{vb["seite"]}">Vorbericht als eigene Seite öffnen</a></p>\n'
    return artikel(vb["titel"], vb["datum"], "", vorspann, vb["text"], [], "", schluss, oben_bild=vb.get("bild") or "")


# ---------------------------------------------------------------- Seite
def finde_vorbericht(d, alle):
    """Gewählter Vorbericht; ohne Wahl der neueste Vorbericht bis 10 Tage vor dem Spiel."""
    wahl = ((d.get("spiel") or {}).get("vorbericht") or "").strip()
    vbs = [x for x in alle if x.get("rubrik") == "Vorbericht"]
    if wahl == "-":
        return None
    if wahl:
        return next((x for x in vbs if x["slug"] == wahl), None)
    import datetime
    spieltag = (d.get("spiel") or {}).get("spieldatum") or d["datum"]
    bis = datetime.date.fromisoformat(spieltag)
    passend = [x for x in vbs if 0 <= (bis - datetime.date.fromisoformat(x["datum"])).days <= 10]
    gegner = ((d.get("spiel") or {}).get("gegner") or "").strip().lower()
    if gegner:
        mit_name = [x for x in passend if any(w in (x["titel"] + " " + x["text"]).lower() for w in gegner.split() if len(w) > 3)]
        passend = mit_name or passend
    passend.sort(key=lambda x: (x["datum"], x.get("zeit") or ""), reverse=True)
    return passend[0] if passend else None


def pfade_fuer_seiten(t):
    """Pfade vom Hauptordner aus auf seiten/ umschreiben."""
    t = re.sub(r'\b(src|href|data-gross)="(?!https?:|mailto:|tel:|#|\.\./|data:|//)([^"]+)"', r'\1="../\2"', t)
    t = re.sub(r"url\((?!https?:|data:|\.\./)([^)]+)\)", r"url(../\1)", t)
    return t


def baue(d, vorlage, alle_beitraege, adresse):
    """Fertige HTML-Seite (für seiten/) zu einem Spielbericht-Beitrag."""
    sp = d.get("spiel") or {}
    s = Spiel(sp, d)
    titel = d["titel"]
    teaser = d["teaser"] if d.get("teaser") and not platzhalter(d["teaser"]) else ""
    # Steht der Anreißer schon als erster Absatz im Text (langer Einstieg), nicht doppelt zeigen
    vorspann = "" if teaser and nur_text(d["text"]).startswith(teaser.rstrip(" …")[:80]) else teaser
    # Bild 1 = Titelbild (Bildkopf), Bild 2-4 in den Text, alle weiteren in die Galerie
    alle = ([d["bild"]] if d.get("bild") else []) + [g for g in (d.get("galerie") or []) if g != d.get("bild")]
    titelbild = alle[0] if alle else "assets/hero.jpg"
    im_text, fuer_galerie = alle[1:4], alle[4:]
    vb = finde_vorbericht(d, alle_beitraege)

    bericht = artikel(titel, d["datum"], sp.get("autor"), vorspann, d["text"], im_text,
                      f"{s.gegner and ('SCH gegen ' + s.gegner) or titel} (Foto: SCH)", spieldaten(s),
                      kicker=(sp.get("kurztitel") or "").strip())
    reiter = [
        ("spielinfo", "Spielinfo", spielinfo(s), ""),
        ("spielbericht", "Spielbericht", bericht, ""),
        ("galerie", "Galerie", galerie(fuer_galerie, titel), ""),
        ("liveticker", "Liveticker", ticker(s, teaser), ""),
        ("stimmen", "Stimmen", stimmen(s), ""),
        ("statistiken", "Statistiken", statistik(s), "grau"),
        ("aufstellung", "Aufstellung", aufstellungen(s), ""),
        ("vorbericht", "Vorbericht", vorbericht_html(vb), ""),  # Vorbericht als letzter Reiter
    ]
    reiter = [r for r in reiter if r[2]]
    knoepfe = "".join(
        f'<button type="button" role="tab" id="sb-tab-{n}" data-name="{n}" aria-controls="sb-{n}" '
        f'aria-selected="{"true" if n == "spielbericht" else "false"}" tabindex="{0 if n == "spielbericht" else -1}">{l}</button>'
        for n, l, _, _ in reiter)
    bereiche = "\n\n".join(
        f'<section class="sb-bereich{" " + k if k else ""}" id="sb-{n}" role="tabpanel" aria-labelledby="sb-tab-{n}"'
        f'{"" if n == "spielbericht" else " hidden"}>\n{inhalt}\n</section>'
        for n, _, inhalt, k in reiter)
    main = (f'<main class="sb">\n<header class="sb-held sb-held-ganz">'
            f'<img class="sb-held-bild" src="{titelbild}" alt="" fetchpriority="high"><h1 class="stitel" data-sb-titel>Spielbericht</h1></header>\n\n'
            f'{tafel(s)}\n\n<div class="sb-reiter-band"><div class="sb-reiter" role="tablist" aria-label="Bereiche des Spielberichts">{knoepfe}</div></div>\n\n'
            f"{bereiche}\n</main>")

    kopf = vorlage[:vorlage.find('<main class="sb">')]
    fuss = vorlage[vorlage.find("</main>") + len("</main>"):]
    voll_titel = f"{e(titel)} · 1. SC 1911 Heiligenstadt"
    beschreibung = e(teaser or (f"Spielbericht: SCH gegen {s.gegner}" if s.gegner else titel))
    kopf = re.sub(r"<title>.*?</title>", f"<title>{voll_titel}</title>", kopf, count=1, flags=re.S)
    kopf = re.sub(r'(<meta name="description" content=")[^"]*', lambda m: m.group(1) + beschreibung, kopf, count=1)
    kopf = re.sub(r'(<meta property="og:title" content=")[^"]*', lambda m: m.group(1) + voll_titel, kopf, count=1)
    kopf = re.sub(r'(<meta property="og:description" content=")[^"]*', lambda m: m.group(1) + beschreibung, kopf, count=1)
    kopf = re.sub(r'(<meta property="og:url" content=")[^"]*', lambda m: m.group(1) + adresse + "seiten/" + d["seite"], kopf, count=1)
    kopf = re.sub(r'(<meta property="og:image" content=")[^"]*', lambda m: m.group(1) + adresse + titelbild, kopf, count=1)
    seite = pfade_fuer_seiten(kopf + main + fuss)
    # og:-Adressen sind absolut und bleiben; der Link auf die Vorberichtsseite liegt danach unter ../seiten/
    return seite, vb


def live_seite(vorlage, adresse):
    """seiten/live.html: Live-Ticker (Inhalt kommt von live.js) im Rahmen der Spielbericht-Seiten."""
    kopf = vorlage[:vorlage.find('<main class="sb">')]
    fuss = vorlage[vorlage.find("</main>") + len("</main>"):]
    titel = "Liveticker · 1. SC 1911 Heiligenstadt"
    beschreibung = "Die Spiele des SCH live: Spielstand, Tore, Wechsel und Karten aus dem FuPa-Liveticker."
    kopf = re.sub(r"<title>.*?</title>", f"<title>{titel}</title>", kopf, count=1, flags=re.S)
    kopf = re.sub(r'(<meta name="description" content=")[^"]*', lambda m: m.group(1) + beschreibung, kopf, count=1)
    kopf = re.sub(r'(<meta property="og:title" content=")[^"]*', lambda m: m.group(1) + titel, kopf, count=1)
    kopf = re.sub(r'(<meta property="og:description" content=")[^"]*', lambda m: m.group(1) + beschreibung, kopf, count=1)
    kopf = re.sub(r'(<meta property="og:url" content=")[^"]*', lambda m: m.group(1) + adresse + "seiten/live.html", kopf, count=1)
    kopf = kopf.replace("</head>", '<link rel="stylesheet" href="live.css?v=1">\n</head>', 1)
    main = ('<main class="sb lv-seite">\n<header class="lv-kopf"><p>1. SC 1911 Heiligenstadt</p><h1 class="stitel">Liveticker</h1></header>\n'
            '<div id="sch-live-seite"><noscript><p>Der Liveticker braucht JavaScript.</p></noscript></div>\n'
            '<script src="live.js?v=1" data-basis="../" defer></script>\n</main>')
    return pfade_fuer_seiten(kopf + main + fuss)
