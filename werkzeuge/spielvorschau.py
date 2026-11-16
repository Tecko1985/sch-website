"""Spielinfo-Seiten für kommende Spiele der 1. Mannschaft (beim Seitenbau, werkzeuge/beitraege.py).

Für jedes noch nicht gespielte Spiel (FuPa) entsteht seiten/spiel-<datum>-<gegner>.html im Aufbau der
Spielbericht-Seiten: Bildkopf „Spielinfo“, Tafel mit beiden Wappen, Reiter Spielinfo, Tabelle und – falls
in der Redaktion vorhanden – Vorbericht. Die Spielkarte unter „Aktuelle Spiele“ verlinkt darauf.
Tabelle und Spieldaten holt der Seitenbau bei FuPa; Besucher laden nichts von FuPa.
Ohne Netz oder bei FuPa-Störung entsteht nichts, und die Karten verlinken wie bisher auf FuPa.
"""
import datetime
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fupa_ticker  # noqa: E402
import spielbericht as sb  # noqa: E402

CLUB = "1-sc-1911-heiligenstadt"
TEAMS = ["m1", "m2"]  # Mannschaften mit Spielinfo-Seiten
TITELBILD = "assets/hero-mannschaft-1600.webp"
TITELBILD_ZWEITE = "assets/zweite-titel.webp"  # Spielinfo-Seiten der 2. Mannschaft
TITELBILD_JUGEND = "assets/nachwuchs-instagram.webp"  # Spielinfo- und Ergebnisseiten des Nachwuchs
e = html.escape


def saison(heute=None):
    h = heute or datetime.date.today()
    j = h.year if h.month >= 7 else h.year - 1
    return f"{j}-{str(j + 1)[2:]}"


def kommende(team):
    liste = fupa_ticker.hole_json(f"{fupa_ticker.API}/v1/teams/{CLUB}-{team}-{saison()}/matches?flavor=current")
    return [m for m in liste if m.get("section") == "PRE" and m.get("homeGoal") is None]


def tabelle(liga_slug):
    """Tabelle aus der FuPa-Tabellenseite (eingebetteter Seitenzustand)."""
    seite = fupa_ticker.hole_text(f"https://www.fupa.net/league/{liga_slug}/standing")
    for skript in re.findall(r"<script[^>]*>(.*?)</script>", seite, re.S):
        if '"standings"' not in skript:
            continue
        zustand = json.loads(skript[skript.find("{"):skript.rfind("}") + 1])
        stapel = [zustand]
        while stapel:
            o = stapel.pop()
            if isinstance(o, dict):
                if isinstance(o.get("standings"), list) and o["standings"] and "rank" in o["standings"][0]:
                    return o["standings"]
                stapel.extend(o.values())
            elif isinstance(o, list):
                stapel.extend(o)
    return []


def ist_sch(team):
    return (team.get("slug") or "").startswith(CLUB + "-")


def wappen(team):
    if ist_sch(team):
        return sb.SCH_WAPPEN
    return sb.wappen_fuer(fupa_ticker._teamname(team)) or sb.LEER_WAPPEN


def tabelle_html(zeilen, hervor):
    if not zeilen:
        return ""
    reihen = []
    for z in zeilen:
        t = z.get("team") or {}
        klasse = ' class="sb-wir"' if ist_sch(t) else ' class="sb-gegner"' if t.get("slug") in hervor else ""
        reihen.append(
            f'<tr{klasse}><td class="sb-platz">{z["rank"]}</td>'
            f'<td class="sb-verein"><img src="{wappen(t)}" alt="" width="28" height="28" loading="lazy"><span>{e(fupa_ticker._teamname(t))}</span></td>'
            f'<td>{z["matches"]}</td><td class="sb-breit">{z["wins"]}</td><td class="sb-breit">{z["draws"]}</td><td class="sb-breit">{z["defeats"]}</td>'
            f'<td class="sb-breit">{z["ownGoals"]}:{z["againstGoals"]}</td><td>{z["goalDifference"]:+d}</td><td class="sb-punkte">{z["points"]}</td></tr>')
    return ('<div class="sb-schmal">\n<h2 class="sb-h2 stitel">Tabelle</h2>\n<div class="sb-tabelle-rahmen"><table class="sb-tabelle">'
            '<thead><tr><th>Pl.</th><th class="sb-verein">Mannschaft</th><th title="Spiele">Sp.</th><th class="sb-breit" title="Siege">S</th>'
            '<th class="sb-breit" title="Unentschieden">U</th><th class="sb-breit" title="Niederlagen">N</th><th class="sb-breit">Tore</th>'
            '<th title="Tordifferenz">Diff.</th><th title="Punkte">Pkt.</th></tr></thead>\n<tbody>' + "".join(reihen) + '</tbody></table></div>\n'
            f'<p class="sb-hinweis">Quelle: FuPa, Stand {datetime.date.today().strftime("%d.%m.%Y")}.</p>\n</div>')


def vorbericht(slug, spieldatum, gegner, beitraege):
    """Vorbericht aus der Redaktion: in der Redaktion diesem Spiel zugeordnet (Feld spiel_slug), sonst
    automatisch bis 10 Tage vor dem Spiel mit dem Gegner im Titel oder Text (nur nicht zugeordnete)."""
    vbs = [x for x in beitraege if x.get("rubrik") == "Vorbericht"]
    gewaehlt = sorted((x for x in vbs if x.get("spiel_slug") == slug), key=lambda x: (x["datum"], x.get("zeit") or ""))
    if gewaehlt:
        return gewaehlt[-1]
    tag = datetime.date.fromisoformat(spieldatum)
    worte = sb.gegner_worte(gegner)
    passend = [x for x in vbs if not x.get("spiel_slug")
               and 0 <= (tag - datetime.date.fromisoformat(x["datum"])).days <= 10
               and any(w in (x["titel"] + " " + x["text"]).lower() for w in worte)]
    passend.sort(key=lambda x: (x["datum"], x.get("zeit") or ""), reverse=True)
    return passend[0] if passend else None


def team_von(m):
    for t in (m["homeTeam"], m["awayTeam"]):
        if ist_sch(t):
            return re.sub(r"-\d{4}-\d{2}$", "", t["slug"][len(CLUB) + 1:])
    return "m1"


def seitenname(m):
    gegner = m["awayTeam"] if ist_sch(m["homeTeam"]) else m["homeTeam"]
    kurz = re.sub(r"-(m\d|u\d+(-\d)?)-\d{4}-\d{2}$", "", gegner.get("slug") or "gegner")
    team = team_von(m)
    zusatz = "zweite-" if team == "m2" else "" if team == "m1" else f"{team}-"
    return f"spiel-{zusatz}{m['kickoff'][:10]}-{kurz}.html"


def wir_name(team):
    """Kurzbezeichnung für Titel und Tabelle: SCH, SCH II, SCH U17 …"""
    if team == "m2":
        return "SCH II"
    if team == "m1":
        return "SCH"
    return f"SCH {sb.MANNSCHAFTEN.get(team, '')}".strip()


def wettbewerb_name(liga, team):
    """Liga wie auf FuPa; beim Nachwuchs ohne „B-Jun“ usw. (die Altersklasse steht schon davor: „U17 · Verbandsliga“)."""
    name = liga.get("middleName") or liga.get("name") or ""
    if team not in ("m1", "m2"):
        name = re.sub(r"^[A-G]-Jun(?:ioren)?\.?\s+", "", name)
        name = re.sub(r"\bVL\b", "Verbandsliga", name)
        name = re.sub(r"\bKOL\b", "Kreisoberliga", name)
        name = re.sub(r"\bSt\.\s*(\d)", r"Staffel \1", name)
        name = re.sub(r"\bTalente\b(?!liga)", "Talenteliga", name)
    return name


def titelbild(team):
    return TITELBILD_ZWEITE if team == "m2" else TITELBILD if team == "m1" else TITELBILD_JUGEND


def baue_seite(m, d, standings, vorlage, adresse, beitraege):
    heim = ist_sch(m["homeTeam"])
    gegner_t = m["awayTeam"] if heim else m["homeTeam"]
    gegner = fupa_ticker._teamname(gegner_t)
    runde = d.get("round") or {}
    liga = runde.get("competitionSeason") or {}
    venue = d.get("venue") or {}
    anstoss = datetime.datetime.fromisoformat(m["kickoff"])
    team = team_von(m)
    sp = {"gegner": gegner, "ort_art": "heim" if heim else "auswaerts", "mannschaft": team,
          "wettbewerb": wettbewerb_name(liga, team),
          "runde": f'{runde["number"]}. Spieltag' if runde.get("type") == "league" and runde.get("number") else "",
          "spieldatum": m["kickoff"][:10], "anstoss": anstoss.strftime("%H:%M"), "spielort": venue.get("name") or ""}
    s = sb.Spiel(sp, {"datum": sp["spieldatum"]})
    s.wappen = wappen(gegner_t)
    tafel = sb.tafel(s).replace('<span class="sb-status">Spielbericht</span>',
                                f'<span class="sb-status">Anpfiff {sp["anstoss"]} Uhr</span>')

    platz = {(z.get("team") or {}).get("slug"): z for z in standings}
    felder = [("Wettbewerb", sp["wettbewerb"]), ("Runde", sp["runde"]),
              ("Anstoß", f'{sb.datum_tag(sp["spieldatum"])}, {sp["anstoss"]} Uhr'),
              ("Spielort", ", ".join(x for x in (venue.get("name"), " ".join(x for x in (venue.get("postcode"), venue.get("city")) if x)) if x))]
    for t in (m["homeTeam"], m["awayTeam"]):
        z = platz.get(t.get("slug"))
        if z:
            felder.append((f'Tabelle {wir_name(team) if ist_sch(t) else gegner}', f'{z["rank"]}. Platz · {z["points"]} Punkte'))
    dl = "\n".join(f"<div><dt>{e(a)}</dt><dd>{e(b)}</dd></div>" for a, b in felder if b)
    links = [f'<a href="seiten/live.html#{e(m["slug"])}">Liveticker am Spieltag</a>']
    if standings:
        links.append('<a href="#tabelle" data-sb-zu="tabelle">Zur Tabelle</a>')
    links.append('<a href="seiten/termine.html">Alle Termine</a>')
    info = (f'<div class="sb-schmal">\n<h2 class="sb-h2 stitel">Spielinfo</h2>\n<dl class="sb-info">\n{dl}\n</dl>\n'
            f'<p class="sb-hinweis">{" · ".join(links)}</p>\n</div>')
    # Vorberichte gibt es nur für die Herren; beim Nachwuchs würde die Gegner-Suche fremde Vorberichte finden
    vb = vorbericht(m["slug"], sp["spieldatum"], gegner, beitraege) if team in ("m1", "m2") else None
    hervor = {gegner_t.get("slug")}
    reiter = [("spielinfo", "Spielinfo", info, ""),
              ("tabelle", "Tabelle", tabelle_html(standings, hervor), ""),
              ("vorbericht", "Vorbericht", sb.vorbericht_html(vb), "")]
    wir = wir_name(team)
    paar = f"{wir} gegen {gegner}" if heim else f"{gegner} gegen {wir}"
    titel = f"Spielinfo: {paar}"
    beschreibung = f'{paar} am {sb.datum_tag(sp["spieldatum"])}, {sp["anstoss"]} Uhr' + (f' – {sp["wettbewerb"]}' if sp["wettbewerb"] else "")
    return sb.rahmen(vorlage, adresse, seitenname(m), titel, beschreibung, titelbild(team), tafel, reiter, "spielinfo")


def baue_alle(ziel, vorlage, adresse, beitraege):
    """Schreibt die Seiten nach <ziel>/seiten/ und liefert {FuPa-Slug: "seiten/<datei>"}."""
    links, tabellen, liste_fuer_redaktion = {}, {}, []
    for team in TEAMS:
        try:
            spiele = kommende(team)
        except Exception as fehler:
            print(f"  Spielinfo {team}: FuPa nicht erreichbar ({fehler})")
            continue
        for m in spiele:
            try:
                d = fupa_ticker.spiel(m["slug"])
                liga = ((d.get("round") or {}).get("competitionSeason") or {}).get("slug")
                if liga and liga not in tabellen:
                    try:
                        tabellen[liga] = tabelle(liga)
                    except Exception as fehler:
                        print(f"  Tabelle {liga}: {fehler}")
                        tabellen[liga] = []
                seite = baue_seite(m, d, tabellen.get(liga) or [], vorlage, adresse, beitraege)
                open(os.path.join(ziel, "seiten", seitenname(m)), "w", encoding="utf-8").write(seite)
                links[m["slug"]] = "seiten/" + seitenname(m)
                heim = ist_sch(m["homeTeam"])
                runde = d.get("round") or {}
                liste_fuer_redaktion.append({
                    "slug": m["slug"], "anstoss": m["kickoff"], "heim": heim,
                    "mannschaft": sb.MANNSCHAFTEN.get(team_von(m), ""),
                    "gegner": fupa_ticker._teamname(m["awayTeam"] if heim else m["homeTeam"]),
                    "wettbewerb": (runde.get("competitionSeason") or {}).get("middleName") or "",
                    "seite": "seiten/" + seitenname(m)})
            except Exception as fehler:
                print(f"  Spielinfo {m.get('slug')}: {fehler}")
    print(f"{len(links)} Spielinfo-Seiten gebaut.")
    # Für die Redaktion: Auswahl „Zu welchem Spiel?“ beim Vorbericht
    liste_fuer_redaktion.sort(key=lambda x: x["anstoss"])
    with open(os.path.join(ziel, "assets", "kommende-spiele.json"), "w", encoding="utf-8") as f:
        json.dump(liste_fuer_redaktion, f, ensure_ascii=False, indent=1)
    return links


# ---------------------------------------------------------------- Nachwuchs (16.11.2026)
# Alle Nachwuchsspiele, die unter „Aktuelle Spiele“ stehen, bekommen eine eigene Seite:
#  - noch nicht gespielt: Spielinfo-Seite wie bei den Herren (ohne Vorbericht)
#  - gespielt: Ergebnisseite mit Tafel, Torschützen des SCH und einem kurzen, sachlichen Satz.
# Gibt es in der Redaktion einen Spielbericht, verlinkt die Karte darauf (spiele.verlinke_berichte, läuft danach).
# Die Seiten erscheinen nicht in den News. Namen: nur Torschützen des SCH, keine Aufstellungen, keine Tickertexte.

def _mit_artikel(name, art):
    """„beim FSV Waltershausen“ / „bei der SG …“, „dem SV …“ / „der JSG …“, „vom …“ / „von der …“."""
    weiblich = bool(re.match(r"^(J?SG|JFG|Spielgemeinschaft)\b", name or ""))
    if art == "bei":
        return f"bei der {name}" if weiblich else f"beim {name}"
    if art == "von":
        return f"von der {name}" if weiblich else f"vom {name}"
    return f"der {name}" if weiblich else f"dem {name}"


def kurztext(team, heim, gegner, es, eg, hz, sch_tore):
    """Kurzer, sachlicher Spielbericht aus den Daten (keine erfundenen Szenen)."""
    wer = f"Die {sb.MANNSCHAFTEN.get(team, '')} des SCH".replace("  ", " ")
    if es > eg:
        satz = f"{wer} gewann {'zu Hause gegen ' + gegner if heim else 'auswärts ' + _mit_artikel(gegner, 'bei')} mit {es}:{eg}."
    elif es < eg:
        satz = f"{wer} musste sich {'zu Hause ' if heim else 'auswärts '}{_mit_artikel(gegner, 'dem')} mit {es}:{eg} geschlagen geben."
    else:
        satz = f"{wer} trennte sich {'zu Hause ' if heim else 'auswärts '}{_mit_artikel(gegner, 'von')} {es}:{eg} unentschieden."
    saetze = [satz]
    if hz:
        saetze.append(f"Zur Pause stand es {hz[0]}:{hz[1]}.")
    if sch_tore:
        zaehl = {}
        for n in sch_tore:
            zaehl[n] = zaehl.get(n, 0) + 1
        namen = [f"{n} ({k})" if k > 1 else n for n, k in zaehl.items()]
        liste = namen[0] if len(namen) == 1 else ", ".join(namen[:-1]) + " und " + namen[-1]
        saetze.append(f"{'Das Tor' if len(sch_tore) == 1 else 'Die Tore'} für den SCH {'erzielte' if len(namen) == 1 else 'erzielten'} {liste}.")
    return " ".join(saetze)


def tore_und_pause(slug, heim, gegner, end):
    """Tore im Vereinsformat („1:0 Name (12.)“, Stand Heim:Gast) und Halbzeitstand aus dem FuPa-Ticker.
    Gegentore ohne Spielernamen. Stimmen die Tore nicht mit dem Endstand überein, keine Torliste."""
    try:
        ev = fupa_ticker.ereignisse(fupa_ticker.stream(slug))
    except Exception:
        return [], [], None
    tore = sorted((x for x in ev if x.get("art") == "tor" and re.match(r"^\d+:\d+$", x.get("stand") or "")),
                  key=lambda x: x["sort"])
    zeilen_, sch_namen, vor = [], [], (0, 0)
    for x in tore:
        h, g = (int(v) for v in x["stand"].split(":"))
        heim_tor = h > vor[0]
        vor = (h, g)
        # Wer getroffen hat, ergibt der Spielstand (FuPa benennt die Teams im Ticker uneinheitlich)
        if heim_tor == heim:
            name = (x.get("_tor") or "").strip() or "SCH"
            if name != "SCH":
                sch_namen.append(name)
        else:
            name = gegner
        zeilen_.append(f'{x["stand"]} {name} ({x["min"]}.)')
    if len(zeilen_) != sum(end):
        zeilen_, sch_namen = [], []
    hz = None
    for x in sorted(ev, key=lambda x: x["sort"]):
        if x.get("art") == "pfiff" and re.search(r"halbzeit|pause", x.get("kopf") or "", re.I) and x.get("stand"):
            h, g = (int(v) for v in x["stand"].split(":"))
            hz = (h, g) if heim else (g, h)
            break
    return zeilen_, sch_namen, hz


def baue_ergebnis(m, d, standings, vorlage, adresse):
    heim = ist_sch(m["homeTeam"])
    gegner_t = m["awayTeam"] if heim else m["homeTeam"]
    gegner = fupa_ticker._teamname(gegner_t)
    team = team_von(m)
    runde = d.get("round") or {}
    liga = runde.get("competitionSeason") or {}
    venue = d.get("venue") or {}
    anstoss = datetime.datetime.fromisoformat(m["kickoff"])
    hg, ag = int(d.get("homeGoal") if d.get("homeGoal") is not None else m["homeGoal"]), \
        int(d.get("awayGoal") if d.get("awayGoal") is not None else m["awayGoal"])
    es, eg = (hg, ag) if heim else (ag, hg)
    tore, sch_namen, hz = tore_und_pause(m["slug"], heim, gegner, (hg, ag))
    sp = {"gegner": gegner, "ort_art": "heim" if heim else "auswaerts", "mannschaft": team,
          "wettbewerb": wettbewerb_name(liga, team),
          "runde": f'{runde["number"]}. Spieltag' if runde.get("type") == "league" and runde.get("number") else "",
          "spieldatum": m["kickoff"][:10], "anstoss": anstoss.strftime("%H:%M"), "spielort": venue.get("name") or "",
          "end_sch": str(es), "end_geg": str(eg), "tore_sch": "\n".join(tore)}
    if hz:
        sp["hz_sch"], sp["hz_geg"] = str(hz[0]), str(hz[1])
    s = sb.Spiel(sp, {"datum": sp["spieldatum"]})
    s.wappen = wappen(gegner_t)
    tafel = sb.tafel(s)
    platz = {(z.get("team") or {}).get("slug"): z for z in standings}
    felder = [("Wettbewerb", sp["wettbewerb"]), ("Runde", sp["runde"]),
              ("Anstoß", f'{sb.datum_tag(sp["spieldatum"])}, {sp["anstoss"]} Uhr'),
              ("Spielort", ", ".join(x for x in (venue.get("name"), " ".join(x for x in (venue.get("postcode"), venue.get("city")) if x)) if x)),
              ("Endstand", s.stand(s.end)), ("Halbzeit", s.stand(s.hz) if s.hz else "")]
    for t in (m["homeTeam"], m["awayTeam"]):
        z = platz.get(t.get("slug"))
        if z:
            felder.append((f'Tabelle {wir_name(team) if ist_sch(t) else gegner}', f'{z["rank"]}. Platz · {z["points"]} Punkte'))
    dl = "\n".join(f"<div><dt>{e(a)}</dt><dd>{e(b)}</dd></div>" for a, b in felder if b)
    links = []
    if standings:
        links.append('<a href="#tabelle" data-sb-zu="tabelle">Zur Tabelle</a>')
    links.append('<a href="seiten/nachwuchs.html">Unser Nachwuchs</a>')
    text = kurztext(team, heim, gegner, es, eg, hz, sch_namen)
    info = (f'<div class="sb-schmal">\n<h2 class="sb-h2 stitel">Kurzbericht</h2>\n<p class="sb-kurz">{e(text)}</p>\n'
            f'<dl class="sb-info">\n{dl}\n</dl>\n<p class="sb-hinweis">{" · ".join(links)}</p>\n</div>')
    reiter = [("spielinfo", "Spielinfo", info, ""),
              ("tabelle", "Tabelle", tabelle_html(standings, {gegner_t.get("slug")}), "")]
    wir = wir_name(team)
    paar = f"{wir} gegen {gegner}" if heim else f"{gegner} gegen {wir}"
    h, g = hg, ag
    titel = f"{paar} {h}:{g}"
    beschreibung = text
    return sb.rahmen(vorlage, adresse, seitenname(m), titel, beschreibung, titelbild(team), tafel, reiter, "spielinfo")


def baue_jugend(ziel, start, vorlage, adresse, beitraege):
    """Seiten für alle Nachwuchsspiele auf den Karten der Startseite. Liefert {FuPa-Slug: "seiten/<datei>"}."""
    links, tabellen = {}, {}
    slugs = [s for s in re.findall(r'<a class="sch-game[^"]*"[^>]*data-spiel="([^"]+)"', start)
             if re.search(rf"{CLUB}-u\d+-\d-", s)]
    # Die Spieldetails nennen beim Nachwuchs keinen Wettbewerb; der steht im Spielplan der Mannschaft
    plan = {}
    for team in sorted({re.search(rf"{CLUB}-(u\d+-\d)-", s).group(1) for s in slugs}):
        for art in ("past&limit=15", "current"):
            try:
                for x in fupa_ticker.hole_json(f"{fupa_ticker.API}/v1/teams/{CLUB}-{team}-{saison()}/matches?flavor={art}") or []:
                    plan[x.get("slug")] = x
            except Exception as fehler:
                print(f"  Spielplan {team}: {fehler}")
    for slug in dict.fromkeys(slugs):
        try:
            d = fupa_ticker.spiel(slug)
            aus_plan = plan.get(slug) or {}
            if not ((d.get("round") or {}).get("competitionSeason")) and (aus_plan.get("round") or {}).get("competitionSeason"):
                d["round"] = aus_plan["round"]
            m = {"slug": slug, "homeTeam": d["homeTeam"], "awayTeam": d["awayTeam"], "kickoff": d["kickoff"],
                 "homeGoal": d.get("homeGoal"), "awayGoal": d.get("awayGoal")}
            if team_von(m) in ("m1", "m2"):
                continue
            liga = ((d.get("round") or {}).get("competitionSeason") or {}).get("slug")
            if liga and liga not in tabellen:
                try:
                    tabellen[liga] = tabelle(liga)
                except Exception as fehler:
                    print(f"  Tabelle {liga}: {fehler}")
                    tabellen[liga] = []
            stand = tabellen.get(liga) or []
            if d.get("homeGoal") is not None and d.get("awayGoal") is not None:
                seite = baue_ergebnis(m, d, stand, vorlage, adresse)
            else:
                seite = baue_seite(m, d, stand, vorlage, adresse, beitraege)
            open(os.path.join(ziel, "seiten", seitenname(m)), "w", encoding="utf-8").write(seite)
            links[slug] = "seiten/" + seitenname(m)
        except Exception as fehler:
            print(f"  Nachwuchsspiel {slug}: {fehler}")
    print(f"{len(links)} Nachwuchs-Spielseiten gebaut.")
    return links


MANNSCHAFTSSEITEN = {"seiten/erste-mannschaft.html": "", "seiten/zweite-mannschaft.html": "zweite-"}


def verlinke_mannschaftsseiten(ziel, links):
    """„Nächste Spiele“ auf den Mannschaftsseiten (im gebauten Ordner): „Zum Spiel“ zeigt auf unsere eigene
    Spielinfo-Seite statt auf fussball.de. Zuordnung über Mannschaft und Spieltag (Datum)."""
    for datei, zusatz in MANNSCHAFTSSEITEN.items():
        pfad = os.path.join(ziel, datei)
        if not os.path.exists(pfad):
            continue
        # TT.MM. -> Seitenname (nur Seiten dieser Mannschaft)
        nach_tag = {}
        for seite in links.values():
            name = seite.split("/")[-1]
            m = re.match(r"spiel-(zweite-)?(\d{4})-(\d{2})-(\d{2})-", name)
            if m and (m.group(1) or "") == zusatz:
                nach_tag[f"{m.group(4)}.{m.group(3)}."] = name

        def ersetze(li):
            t = li.group(0)
            tag = re.search(r'<span class="tm-team"><b>\w+, (\d{2}\.\d{2}\.)</b>', t)
            if not tag or tag.group(1) not in nach_tag:
                return t
            return re.sub(r'<a href="[^"]*">Zum Spiel', f'<a href="{nach_tag[tag.group(1)]}">Zum Spiel', t, count=1)

        s = open(pfad, encoding="utf-8").read()
        k = s.find("<h2>Nächste Spiele</h2>")
        if k < 0:
            continue
        e = s.find("</ul>", k)
        neu = s[:k] + re.sub(r'<li class="tm-spiel[^"]*">.*?</li>', ersetze, s[k:e], flags=re.S) + s[e:]
        if neu != s:
            open(pfad, "w", encoding="utf-8").write(neu)


def verlinke_karten(start, links):
    """Spielkarten (noch mit FuPa-Link) auf die eigene Seite zeigen lassen: kommende Spiele auf die
    Spielinfo-Seite, gespielte Nachwuchsspiele auf die Ergebnisseite (Redaktionsberichte setzt danach
    spiele.verlinke_berichte und haben damit Vorrang)."""
    def ersetze(treffer):
        a = treffer.group(0)
        slug = re.search(r'data-spiel="([^"]+)"', a).group(1)
        if slug not in links or "fupa.net/match/" not in a:
            return a
        if "sch-upcoming" not in a and not re.search(rf"{CLUB}-u\d+-\d-", slug):
            return a
        return re.sub(r'href="[^"]*"', f'href="{links[slug]}"', a, count=1)
    return re.sub(r'<a class="sch-game[^>]*data-spiel="[^"]+"[^>]*>', ersetze, start)


def vereinsspiele(ziel):
    """assets/vereinsspiele.json: Spiele aller Mannschaften (45 Tage zurück bis 60 Tage voraus) –
    daraus erkennt die Redaktion beim Spielbericht die Mannschaft aus Spieltag und Gegner."""
    heute = datetime.date.today()
    von, bis = (heute - datetime.timedelta(days=45)).isoformat(), (heute + datetime.timedelta(days=60)).isoformat()
    alle = {}
    for team in sb.MANNSCHAFTEN:
        for art in ("past&limit=15", "current"):
            try:
                liste = fupa_ticker.hole_json(f"{fupa_ticker.API}/v1/teams/{CLUB}-{team}-{saison()}/matches?flavor={art}")
            except Exception:
                continue
            for m in liste if isinstance(liste, list) else []:
                if not (von <= m.get("kickoff", "")[:10] <= bis) or team_von(m) != team:
                    continue
                heim = ist_sch(m["homeTeam"])
                alle[m["slug"]] = {"slug": m["slug"], "team": team, "mannschaft": sb.MANNSCHAFTEN[team],
                                   "datum": m["kickoff"][:10], "anstoss": m["kickoff"][11:16], "heim": heim,
                                   "gegner": fupa_ticker._teamname(m["awayTeam"] if heim else m["homeTeam"])}
    liste = sorted(alle.values(), key=lambda x: (x["datum"], x["anstoss"]))
    with open(os.path.join(ziel, "assets", "vereinsspiele.json"), "w", encoding="utf-8") as f:
        json.dump(liste, f, ensure_ascii=False, indent=1)
    print(f"{len(liste)} Vereinsspiele für die Redaktion.")
