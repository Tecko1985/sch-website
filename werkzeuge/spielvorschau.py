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
    zusatz = "zweite-" if team_von(m) == "m2" else ""
    return f"spiel-{zusatz}{m['kickoff'][:10]}-{kurz}.html"


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
          "wettbewerb": liga.get("middleName") or liga.get("name") or "",
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
            felder.append((f'Tabelle {("SCH II" if team == "m2" else "SCH") if ist_sch(t) else gegner}', f'{z["rank"]}. Platz · {z["points"]} Punkte'))
    dl = "\n".join(f"<div><dt>{e(a)}</dt><dd>{e(b)}</dd></div>" for a, b in felder if b)
    links = [f'<a href="seiten/live.html#{e(m["slug"])}">Liveticker am Spieltag</a>']
    if standings:
        links.append('<a href="#tabelle" data-sb-zu="tabelle">Zur Tabelle</a>')
    links.append('<a href="seiten/termine.html">Alle Termine</a>')
    info = (f'<div class="sb-schmal">\n<h2 class="sb-h2 stitel">Spielinfo</h2>\n<dl class="sb-info">\n{dl}\n</dl>\n'
            f'<p class="sb-hinweis">{" · ".join(links)}</p>\n</div>')
    vb = vorbericht(m["slug"], sp["spieldatum"], gegner, beitraege)
    hervor = {gegner_t.get("slug")}
    reiter = [("spielinfo", "Spielinfo", info, ""),
              ("tabelle", "Tabelle", tabelle_html(standings, hervor), ""),
              ("vorbericht", "Vorbericht", sb.vorbericht_html(vb), "")]
    wir = "SCH II" if team == "m2" else "SCH"
    paar = f"{wir} gegen {gegner}" if heim else f"{gegner} gegen {wir}"
    titel = f"Spielinfo: {paar}"
    beschreibung = f'{paar} am {sb.datum_tag(sp["spieldatum"])}, {sp["anstoss"]} Uhr' + (f' – {sp["wettbewerb"]}' if sp["wettbewerb"] else "")
    return sb.rahmen(vorlage, adresse, seitenname(m), titel, beschreibung, TITELBILD, tafel, reiter, "spielinfo")


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


def verlinke_karten(start, links):
    """Kommende Spielkarten (noch mit FuPa-Link) auf die eigene Spielinfo-Seite zeigen lassen."""
    def ersetze(treffer):
        a = treffer.group(0)
        slug = re.search(r'data-spiel="([^"]+)"', a).group(1)
        if slug not in links or "sch-upcoming" not in a or "fupa.net/match/" not in a:
            return a
        return re.sub(r'href="[^"]*"', f'href="{links[slug]}"', a, count=1)
    return re.sub(r'<a class="sch-game[^>]*data-spiel="[^"]+"[^>]*>', ersetze, start)
