"""„Aktuelle Spiele“ auf der Startseite (index.html, Abschnitt sch-matches).

Zwei Aufgaben:
1. Von Hand:  python3 werkzeuge/spiele.py
   Holt Ergebnisse und kommende Spiele von FuPa und baut die Spielkarten der drei Reiter
   (Männer, 2. Mannschaft, Nachwuchs) neu, mit Stand von heute. Links auf eigene Spielberichte bleiben.
2. Beim Seitenbau (werkzeuge/beitraege.py): verlinke_berichte() gibt der Karte, zu der ein
   Spielbericht aus der Redaktion gehört, Ergebnis und Link „Zum Spielbericht“.
"""
import datetime
import html
import json
import os
import re
import sys
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLUB = "1-sc-1911-heiligenstadt"
SAISON = "2026-27"
LOGO = '<img src="assets/logo.png" alt="" width="827" height="945">'

# Reiter -> FuPa-Mannschaften (Kürzel im FuPa-Teamnamen), Anzahl gespielter / kommender Karten
REITER = {
    "sch-fixtures-men": {"teams": ["m1"], "zurueck": 3, "vor": 3},
    "sch-fixtures-reserve": {"teams": ["m2"], "zurueck": 3, "vor": 3},
    "sch-fixtures-youth": {"teams": ["u19-1", "u17-1", "u17-2", "u15-1", "u13-1", "u12-2", "u11-2"], "zurueck": 5, "vor": 5},
}
# Nachwuchs: Bezeichnung auf der Karte und ob es eine zweite Mannschaft ist
JUGEND = {"u19-1": ("U19", False), "u17-1": ("U17", False), "u17-2": ("U16", True), "u15-1": ("U15", False),
          "u13-1": ("U13", False), "u12-2": ("U12", True), "u11-2": ("U11 II", True)}
VORSILBEN = {"fc", "sv", "tsv", "fsv", "sg", "bsv", "jfc", "jsg", "spvgg", "sc", "vfb", "vfl", "ssv", "jfv", "1.", "e.v."}


# ---------------------------------------------------------------- Karten
def wettbewerb(name):
    n = name or ""
    if "pokal" in n.lower():
        return "Thüringenpokal"
    if "KOL" in n or "Kreisoberliga" in n:
        return "Kreisoberliga"
    if "Talente" in n:
        return "Talenteliga"
    if re.search(r"\bKL\b|Kreisliga", n):
        return "Kreisliga"
    if re.search(r"Verbandsliga|\bVL\b|Thüringenliga", n):
        return "Verbandsliga"
    return n


def kuerzel(name, bekannt):
    if name in bekannt:
        return bekannt[name]
    worte = [w for w in re.split(r"[\s/\-]+", name) if w and w.lower() not in VORSILBEN and not w.isdigit()]
    if len(worte) >= 3:
        k = "".join(w[0] for w in worte[:3])
    elif len(worte) == 2:
        k = worte[0][0] + worte[1][:2]
    else:
        k = (worte[0] if worte else name)[:3]
    return k.upper()


def zeit(iso):
    d = datetime.datetime.fromisoformat(iso)
    return d.strftime("%d.%m.%Y | %H:%M Uhr")


def team_html(name, ist_sch, kurz, wappen=None):
    e = html.escape(name)
    if ist_sch:
        return f'<span class="sch-matchteam">{LOGO}<b>SCH</b><span class="sch-teamname">{e}</span></span>'
    if wappen:
        return (f'<span class="sch-matchteam"><img src="{html.escape(wappen)}" alt="" width="200" height="200">'
                f'<b>{html.escape(kurz)}</b><span class="sch-teamname">{e}</span></span>')
    return (f'<span class="sch-matchteam"><span class="sch-teammark" aria-hidden="true">{html.escape(kurz)}</span>'
            f'<b>{html.escape(kurz)}</b><span class="sch-teamname">{e}</span></span>')


def karte(sp, bekannt):
    """sp: dict mit kickoff, meta, heim, gast, heim_sch, tore (h, g) oder None, href, bericht"""
    if sp["tore"]:
        h, g = sp["tore"]
        eigene, fremde = (h, g) if sp["heim_sch"] else (g, h)
        art, wort = ("sch-win", "Sieg") if eigene > fremde else ("sch-loss", "Niederlage") if eigene < fremde else ("sch-draw", "Remis")
        kopf = f'<a class="sch-game sch-finished {art}" href="{html.escape(sp["href"])}"><span class="sch-outcome">{wort}</span>'
        stand = f"{h} : {g}"
        link = "Zum Spielbericht" if sp.get("bericht") else "Zur Spielübersicht"
    else:
        kopf = f'<a class="sch-game sch-upcoming" href="{html.escape(sp["href"])}">'
        stand = "–"
        link = "Zum Spielbericht" if sp.get("bericht") else "Zum Spiel"
    heim = team_html(sp["heim"], sp["heim_sch"], kuerzel(sp["heim"], bekannt), sp.get("wappen"))
    gast = team_html(sp["gast"], not sp["heim_sch"], kuerzel(sp["gast"], bekannt), sp.get("wappen"))
    return (f'{kopf}<span class="sch-matchmeta">{html.escape(sp["meta"])}</span>'
            f'<time datetime="{sp["kickoff"]}">{zeit(sp["kickoff"])}</time>'
            f'<span class="sch-gamepair">{heim}<strong class="sch-result">{stand}</strong>{gast}</span>'
            f'<span class="sch-matchlink">{link} <span aria-hidden="true">→</span></span></a>')


# ---------------------------------------------------------------- FuPa
def hole(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SCH-Webseite)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


WAPPEN_ORDNER = "assets/wappen"


def lade_wappen(team):
    """Vereinswappen des Gegners von FuPa als PNG (200 x 200) nach assets/wappen/<verein>.png; gibt den Pfad zurück."""
    verein = (team.get("club") or {}).get("slug") or team.get("clubSlug") or ""
    bild = ((team.get("image") or (team.get("club") or {}).get("image") or {}).get("path") or "")
    if not re.match(r"^[a-z0-9-]+$", verein) or not bild.startswith("https://image.fupa.net/"):
        return None
    pfad = f"{WAPPEN_ORDNER}/{verein}.png"
    ziel = os.path.join(REPO, pfad)
    if not os.path.exists(ziel):
        try:
            req = urllib.request.Request(bild.rstrip("/") + "/200x200.png", headers={"User-Agent": "Mozilla/5.0 (SCH-Webseite)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                daten = r.read()
        except Exception:
            return None
        if not daten.startswith(b"\x89PNG"):
            return None
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        open(ziel, "wb").write(daten)
    return pfad


def teamname(t):
    n = t.get("name")
    return (n.get("full") or n.get("middle")) if isinstance(n, dict) else n


def spiele_von_fupa():
    """Liste aller Spiele (gespielt und kommend) der Mannschaften aus REITER."""
    alle = {}
    teams = [t for r in REITER.values() for t in r["teams"]]
    for t in teams:
        try:
            daten = json.loads(hole(f"https://api.fupa.net/v1/teams/{CLUB}-{t}-{SAISON}/matches?flavor=past&limit=10"))
        except Exception as fehler:  # einzelne Mannschaft ohne Daten: weiter
            print(f"  {t}: keine Ergebnisse ({fehler})", file=sys.stderr)
            continue
        for m in daten if isinstance(daten, list) else []:
            alle[m["slug"]] = m
    # Kommende Spiele aller Mannschaften stehen auf der Vereinsseite (im eingebetteten Seitenzustand)
    seite = hole(f"https://www.fupa.net/club/{CLUB}/matches")
    for skript in re.findall(r"<script[^>]*>(.*?)</script>", seite, re.S):
        if '"kickoff"' not in skript:
            continue
        zustand = json.loads(skript[skript.find("{"):skript.rfind("}") + 1])
        stapel = [zustand]
        while stapel:
            o = stapel.pop()
            if isinstance(o, dict):
                if o.get("kickoff") and o.get("homeTeam") and o.get("awayTeam") and o.get("slug"):
                    alle.setdefault(o["slug"], o)
                else:
                    stapel.extend(o.values())
            elif isinstance(o, list):
                stapel.extend(o)
    return list(alle.values())


def sch_team(m):
    for seite in ("homeTeam", "awayTeam"):
        slug = m[seite].get("slug") or ""
        if slug.startswith(CLUB + "-"):
            return seite, slug[len(CLUB) + 1:].replace("-" + SAISON, "")
    return None, None


# ---------------------------------------------------------------- Startseite neu bauen
def bekannte_kuerzel(block):
    return {html.unescape(n): k for k, n in re.findall(
        r'<b>([^<]+)</b><span class="sch-teamname">([^<]+)</span>', block) if k != "SCH"}


def bekannte_links(block):
    """Bisherige Spielbericht-Links: Datum -> href (nur eigene Seiten, nicht FuPa)."""
    return {d[:10]: h for h, d in re.findall(r'<a class="sch-game[^"]*" href="((?!https?:)[^"]+)">.*?datetime="([^"]+)"', block, re.S)}


def baue_reiter(spiele, reiter_id, regel, bekannt, links, heute):
    karten_daten = []
    for m in spiele:
        seite, team = sch_team(m)
        if team not in regel["teams"]:
            continue
        gespielt = m.get("homeGoal") is not None and m.get("awayGoal") is not None
        if not gespielt and m["kickoff"][:10] < heute:
            continue  # abgesagt oder ohne Ergebnis
        meta = wettbewerb((m.get("competition") or {}).get("middleName") or (m.get("competition") or {}).get("name"))
        heim, gast = teamname(m["homeTeam"]), teamname(m["awayTeam"])
        sch_name = "1. SC Heiligenstadt"
        if team == "m2" or JUGEND.get(team, ("", False))[1]:
            sch_name += " II"
        if team in JUGEND:
            meta = f"{JUGEND[team][0]} · {meta}"
        if seite == "homeTeam":
            heim = sch_name
        else:
            gast = sch_name
        eigener = links.get(m["kickoff"][:10]) if reiter_id != "sch-fixtures-youth" else None
        gegner_team = m["awayTeam"] if seite == "homeTeam" else m["homeTeam"]
        karten_daten.append({
            "kickoff": m["kickoff"], "meta": meta, "heim": heim, "gast": gast, "heim_sch": seite == "homeTeam",
            "tore": (m["homeGoal"], m["awayGoal"]) if gespielt else None,
            "href": eigener or f"https://www.fupa.net/match/{m['slug']}", "bericht": bool(eigener),
            "gegner_team": gegner_team})
    karten_daten.sort(key=lambda k: k["kickoff"])
    fertig = [k for k in karten_daten if k["tore"]][-regel["zurueck"]:]
    kommend = [k for k in karten_daten if not k["tore"]][:regel["vor"]]
    for k in fertig + kommend:  # Wappen nur für Karten, die auch angezeigt werden
        k["wappen"] = lade_wappen(k["gegner_team"])
    return fertig + kommend, max(0, len(fertig) - 1)


def aktualisiere_startseite(pfad=None):
    pfad = pfad or os.path.join(REPO, "index.html")
    t = open(pfad, encoding="utf-8").read()
    s = t.find('<section class="sch-matches"')
    e = t.find("</section>", s)
    block = t[s:e]
    bekannt, links = bekannte_kuerzel(block), bekannte_links(block)
    spiele = spiele_von_fupa()
    heute = datetime.date.today().isoformat()
    neu = block
    for reiter_id, regel in REITER.items():
        karten, start = baue_reiter(spiele, reiter_id, regel, bekannt, links, heute)
        if not karten:
            print(f"  {reiter_id}: keine Spiele gefunden, bleibt wie es ist", file=sys.stderr)
            continue
        a = neu.find(f'id="{reiter_id}"')
        spur = neu.find('<div class="sch-gametrack"', a)
        ende = neu.find("</div>", spur)
        neu = (neu[:spur] + f'<div class="sch-gametrack" data-initial="{start}">' + "".join(karte(k, bekannt) for k in karten)
               + neu[ende:])
        print(f"  {reiter_id}: {len(karten)} Karten")
    stand = datetime.date.today().strftime("%d.%m.%Y")
    neu = re.sub(r"Stand: \d{2}\.\d{2}\.\d{4}", f"Stand: {stand}", neu)
    open(pfad, "w", encoding="utf-8").write(t[:s] + neu + t[e:])


# ---------------------------------------------------------------- Beim Seitenbau: Spielberichte verlinken
def _worte(name):
    return {w for w in re.split(r"[\s/\-.]+", (name or "").lower()) if len(w) > 3 and w not in VORSILBEN and w != "heiligenstadt"}


def verlinke_berichte(t, beitraege):
    """Karte zum Spielbericht finden (gleicher Tag, gleicher Gegner) und Ergebnis + Link setzen."""
    berichte = [d for d in beitraege if d.get("rubrik") == "Spielbericht" and (d.get("spiel") or {}).get("gegner")]
    berichte.sort(key=lambda d: (d["datum"], d.get("zeit") or ""))  # neuester gewinnt
    for d in berichte:
        sp = d["spiel"]
        gegner = _worte(sp["gegner"])
        if sp.get("spieldatum"):
            tage = {sp["spieldatum"]}
        else:  # ohne Spieltag: Spiel gegen diesen Gegner bis 10 Tage vor dem Bericht
            bis = datetime.date.fromisoformat(d["datum"])
            tage = {(bis - datetime.timedelta(days=i)).isoformat() for i in range(11)}

        def ersetze(m):
            karte_alt = m.group(0)
            datum = re.search(r'datetime="(\d{4}-\d{2}-\d{2})', karte_alt)
            if not datum or datum.group(1) not in tage:
                return karte_alt
            namen = re.findall(r'<span class="sch-teamname">([^<]+)</span>', karte_alt)
            if not any(_worte(html.unescape(n)) & gegner for n in namen):
                return karte_alt
            k = re.sub(r'href="[^"]*"', f'href="seiten/{d["seite"]}"', karte_alt, count=1)
            k = re.sub(r'<span class="sch-matchlink">[^<]*', '<span class="sch-matchlink">Zum Spielbericht ', k, count=1)
            es, eg = sp.get("end_sch"), sp.get("end_geg")
            if str(es).isdigit() and str(eg).isdigit():
                es, eg = int(es), int(eg)
                heim_sch = sp.get("ort_art", "heim") != "auswaerts"
                h, g = (es, eg) if heim_sch else (eg, es)
                art, wort = ("sch-win", "Sieg") if es > eg else ("sch-loss", "Niederlage") if es < eg else ("sch-draw", "Remis")
                k = re.sub(r'class="sch-game[^"]*"', f'class="sch-game sch-finished {art}"', k, count=1)
                k = re.sub(r'<span class="sch-outcome">[^<]*</span>', "", k)
                k = k.replace(">", f'><span class="sch-outcome">{wort}</span>', 1)
                k = re.sub(r'<strong class="sch-result">[^<]*</strong>', f'<strong class="sch-result">{h} : {g}</strong>', k)
            return k

        t = re.sub(r'<a class="sch-game[^"]*" href="[^"]*">.*?</a>', ersetze, t, flags=re.S)
    return t


if __name__ == "__main__":
    aktualisiere_startseite()
