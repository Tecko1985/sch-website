"""Termine-Seite (seiten/termine.html) aus dem Vereinsspielplan auf fussball.de neu bauen.

Aufruf:  python3 werkzeuge/termine.py
Holt alle Spiele von heute bis Saisonende (mit Spielort), lässt spielfreie Termine weg,
nimmt die kommenden Wanderungen aus dem Wanderplan auf seiten/wandern.html und die Dartspiele der Carrot Kings
aus dem Spielplan auf seiten/dart.html dazu,
zeigt verlegte Spiele am neuen Termin und markiert abgesetzte. Die Mannschaftsbezeichnung
(z. B. „U13 II“) wird von der bisherigen Seite übernommen (über die fussball.de-Mannschaft);
für neue Mannschaften aus der Altersklasse gebildet.
"""
import datetime
import html
import os
import re
import sys
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEITE = os.path.join(REPO, "seiten", "termine.html")
VEREIN_ID = "00ES8GNC5C0000A8VV0AG08LVUPGND5I"


def saisonende(heute=None):
    """Letzter Tag der laufenden Saison (30. Juni), Saisonwechsel am 1. Juli (Bugjagd 16.11.2026 H2-4)."""
    h = datetime.date.fromisoformat(heute) if isinstance(heute, str) else (heute or datetime.date.today())
    return f"{h.year if h.month < 7 else h.year + 1}-06-30"


SAISONENDE = saisonende()
TAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
MONATE = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August", "September", "Oktober", "November", "Dezember"]
ALTER = {"A": "U19", "B": "U17", "C": "U15", "D": "U13", "E": "U11", "F": "U9", "G": "U7"}


def hole(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (SCH-Webseite)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def spielplan(von, bis):
    """Zeilen des Vereinsspielplans als Liste von dicts."""
    zeilen, offset = [], 0
    while True:
        t = hole(f"https://www.fussball.de/ajax.club.matchplan/-/id/{VEREIN_ID}/mime-type/HTML/mode/PAGE/show-filter/false"
                 f"/max/100/datum-von/{von}/datum-bis/{bis}/show-venues/true/offset/{offset}")
        teile = re.split(r'<tr class="row-headline visible-small">', t)[1:]
        for teil in teile:
            kopf = re.search(r'<td colspan="6">\s*\w+, (\d{2})\.(\d{2})\.(\d{4}) - (\d{2}:\d{2}) Uhr \| ([^|<]+?) \| ([^<]+?)\s*</td>', teil)
            vereine = re.findall(r'<td class="column-club[^"]*">\s*<a href="([^"]*)"[^>]*>.*?<div class="club-name">\s*(.*?)\s*</div>', teil, re.S)
            if not kopf or len(vereine) < 2:
                continue
            spiel = re.search(r'href="(https://www\.fussball\.de/spiel/[^"]+)"', teil)
            info = re.search(r'<span class="info-text">\s*([^<]*?)\s*</span>', teil)
            ort = re.search(r'<tr class="[^"]*row-venue[^"]*">\s*<td></td>\s*<td colspan="3">\s*(.*?)\s*</td>', teil, re.S)
            tag, monat, jahr, uhr, klasse, wettbewerb = kopf.groups()
            zeilen.append({
                "datum": f"{jahr}-{monat}-{tag}", "zeit": uhr, "klasse": klasse.strip(), "wettbewerb": wettbewerb.strip(),
                "heim": html.unescape(vereine[0][1]), "heim_url": vereine[0][0],
                "gast": html.unescape(vereine[1][1]), "gast_url": vereine[1][0],
                "spiel": spiel.group(1) if spiel else "", "info": html.unescape(info.group(1)) if info else "",
                "ort": html.unescape(re.sub(r"\s+", " ", ort.group(1))) if ort else ""})
        if len(teile) < 100:
            return zeilen
        offset += 100


def spiel_id(url):
    m = re.search(r"/spiel/([A-Z0-9]{20,})", url or "")
    return m.group(1) if m else ""


def team_id(url):
    m = re.search(r"/team-id/([A-Z0-9]+)", url or "")
    return m.group(1) if m else ""


def ist_sch(name):
    return "Heiligenstadt" in name and "SC 1911" in name


def alte_bezeichnungen(seite):
    """Spiel-ID -> Mannschaftsbezeichnung von der bisherigen Termine-Seite."""
    return {spiel_id(u): b for b, u in re.findall(
        r'<span class="tm-team"><b>([^<]*)</b>.*?<a href="([^"]*)"', seite)}


def bezeichnung(z, sch_name, nach_team):
    tid = team_id(z["heim_url"] if ist_sch(z["heim"]) else z["gast_url"])
    if tid in nach_team:
        return nach_team[tid]
    zweite = sch_name.rstrip().endswith(" II")
    if z["klasse"].startswith("Herren"):
        return "2. Mannschaft" if zweite else "1. Mannschaft"
    b = ALTER.get(z["klasse"][:1], z["klasse"])
    if "Juniorinnen" in z["klasse"]:
        b += " Mädchen"
    return b + (" II" if zweite else "")


def eintrag(z, label):
    heim_sch = ist_sch(z["heim"])
    art = "herren" if label.endswith("Mannschaft") else "nachwuchs"
    klassen = [art] + (["heim"] if heim_sch else [])
    if z.get("abgesetzt"):
        klassen.append("abgesetzt")
        marke = '<em class="tm-marke ab">Abgesetzt</em>'
    elif z.get("verlegt"):
        marke = f'<em class="tm-marke">{"Heimspiel" if heim_sch else "Auswärts"} · verlegt</em>'
    else:
        marke = '<em class="tm-marke">Heimspiel</em>' if heim_sch else '<em class="tm-marke aus">Auswärts</em>'
    e = lambda s: html.escape(s, quote=True)
    ort = f'<small class="tm-platz">{e(z["ort"])}</small>' if z["ort"] and not z.get("abgesetzt") else ""
    link = (f'<a href="{e(z["spiel"])}">Zum Spiel<span class="tm-sr"> {e(z["heim"])} gegen {e(z["gast"])}</span></a>'
            if z["spiel"] else "")
    return (f'<li class="tm-spiel {" ".join(klassen)}"><span class="tm-zeit">{z["zeit"]}</span>'
            f'<span class="tm-team"><b>{e(label)}</b><small>{e(z["wettbewerb"])}</small></span>'
            f'<span class="tm-paar"><span class="tm-gegner"><span>{e(z["heim"])}</span><i aria-hidden="true">:</i>'
            f'<span>{e(z["gast"])}</span></span>{ort}</span><span class="tm-info">{marke}{link}</span></li>')


WANDERSEITE = os.path.join(REPO, "seiten", "wandern.html")


def wandertermine(heute):
    """Kommende Wanderungen aus dem Wanderplan auf seiten/wandern.html (eine Quelle: Ändert die Redaktion den
    Wanderplan, ändert sich auch die Termine-Seite). Liste von dicts mit datum, zeit, titel, treff, strecke."""
    try:
        s = open(WANDERSEITE, encoding="utf-8").read()
    except OSError:
        return []
    jahr = re.search(r'<h2 id="wp-titel">Wanderplan (\d{4})</h2>', s)
    start = re.search(r"Start (\d{1,2}):(\d{2}) Uhr", s)
    standard = f"{int(start.group(1)):02d}:{start.group(2)}" if start else "10:00"
    aus = []
    for datum, inhalt in re.findall(r'<li><time class="wp-datum" datetime="(\d{4}-\d{2}-\d{2})">.*?</time>'
                                    r'<div class="wp-text">(.*?)</div></li>', s, re.S):
        if datum < heute:
            continue
        titel = re.search(r"<strong>(.*?)</strong>", inhalt)
        feld = lambda name: (re.search(rf"<b>{name}:</b>\s*(.*?)</span>", inhalt, re.S) or [None, ""])[1]
        titel = html.unescape(re.sub(r"<[^>]+>", "", titel.group(1))).strip() if titel else "Wanderung"
        treff = html.unescape(re.sub(r"<[^>]+>", "", feld("Treff"))).strip()
        # Abweichende Zeit: „8:00 Uhr in Heiligenstadt …“ beim Treff (gemeinsame Abfahrt) zuerst,
        # sonst „(Start 8:30–10:30 Uhr)“ im Titel, sonst die Startzeit aus den Eckdaten
        z = re.match(r"(\d{1,2}):(\d{2}) Uhr", treff) or re.search(r"Start (\d{1,2}):(\d{2})", titel)
        aus.append({"datum": datum, "zeit": f"{int(z.group(1)):02d}:{z.group(2)}" if z else standard,
                    "titel": re.sub(r"\s*\(Start [^)]*\)", "", titel), "treff": treff,
                    "strecke": html.unescape(re.sub(r"<[^>]+>", "", feld("Strecke"))).strip(),
                    "plan": f"Wanderplan {jahr.group(1)}" if jahr else "Wanderplan"})
    return aus


def wander_eintrag(w):
    e = lambda s: html.escape(s, quote=True)
    ort = " · ".join(x for x in (f"Treff: {w['treff']}" if w["treff"] else "", w["strecke"]) if x)
    return (f'<li class="tm-spiel wandern"><span class="tm-zeit">{w["zeit"]}</span>'
            f'<span class="tm-team"><b>Wandern</b><small>{e(w["plan"])}</small></span>'
            f'<span class="tm-paar"><span class="tm-gegner"><span>{e(w["titel"])}</span></span>'
            + (f'<small class="tm-platz">{e(ort)}</small>' if ort else "") + '</span>'
            f'<span class="tm-info"><em class="tm-marke wandern">Wanderung</em>'
            f'<a href="wandern.html#wanderplan">Zum Wanderplan<span class="tm-sr"> {e(w["titel"])}</span></a></span></li>')


DARTSEITE = os.path.join(REPO, "seiten", "dart.html")


def dartspiele(heute):
    """Kommende Spiele der Carrot Kings aus dem Spielplan auf seiten/dart.html (eine Quelle)."""
    try:
        s = open(DARTSEITE, encoding="utf-8").read()
    except OSError:
        return []
    aus = []
    for attr in re.findall(r'<li class="dp-spiel[^"]*"([^>]*)>', s):
        a = dict(re.findall(r'data-(\w+)="([^"]*)"', attr))
        if a.get("datum", "") >= heute:
            aus.append({"datum": a["datum"], "zeit": a.get("zeit") or "14:00", "team": html.unescape(a.get("team", "")),
                        "heim": a.get("heim") == "1", "gegner": html.unescape(a.get("gegner", ""))})
    return aus


def dart_eintrag(s):
    e = lambda x: html.escape(x, quote=True)
    wir = "Carrot Kings Heiligenstadt"
    h, g = (wir, s["gegner"]) if s["heim"] else (s["gegner"], wir)   # Heimmannschaft zuerst
    ort = '<small class="tm-platz">Gastwirtschaft „Schwarzer Adler“, Heiligenstadt</small>' if s["heim"] else ""
    marke = '<em class="tm-marke dart">Heimspiel</em>' if s["heim"] else '<em class="tm-marke aus">Auswärts</em>'
    return (f'<li class="tm-spiel dart{" heim" if s["heim"] else ""}"><span class="tm-zeit">{s["zeit"]}</span>'
            f'<span class="tm-team"><b>Dart · {e(s["team"])}</b><small>Carrot Kings</small></span>'
            f'<span class="tm-paar"><span class="tm-gegner"><span>{e(h)}</span><i aria-hidden="true">:</i>'
            f'<span>{e(g)}</span></span>{ort}</span>'
            f'<span class="tm-info">{marke}<a href="dart.html#spielplan">Zum Spielplan'
            f'<span class="tm-sr"> {e(h)} gegen {e(g)}</span></a></span></li>')


def tag_kopf(iso):
    d = datetime.date.fromisoformat(iso)
    wt, mo = TAGE[d.weekday()], MONATE[d.month - 1]
    return (f'<section class="tm-tag" aria-label="{wt}, {d.day}. {mo} {d.year}"><h2><span>{wt}</span> {d.day}. {mo}</h2>'
            f'<ul class="tm-liste">\n')


def eintraege_der_seite(teil):
    """Spiele im Listenteil der Seite: Schlüssel (Spiel-Link) -> lesbare Kurzform mit Datum."""
    aus = {}
    for tag_html in re.findall(r'<section class="tm-tag" aria-label="([^"]*)">(.*?)</section>', teil, re.S):
        tag, inhalt = tag_html
        for li in re.findall(r'<li class="tm-spiel[^"]*">.*?</li>', inhalt, re.S):
            text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<span class=\"tm-sr\">.*?</span>|<[^>]+>", " ", li))).strip()
            link = re.search(r'<a href="([^"]*)"', li)
            paar = re.sub(r"<[^>]+>", "|", re.search(r'<span class="tm-gegner">(.*?)</span></span>', li).group(1))
            schluessel = (spiel_id(link.group(1)) + paar) if link else text
            aus[schluessel] = f"{tag}: {text}"
    return aus


def tag_iso(kurzform):
    m = re.match(r"\w+, (\d+)\. (\w+) (\d{4})", kurzform)
    return f"{m.group(3)}-{MONATE.index(m.group(2)) + 1:02d}-{int(m.group(1)):02d}" if m else ""


# Mannschaftsseiten mit Liste „Nächste Spiele“: Seite -> Bezeichnung auf der Termine-Seite
MANNSCHAFTSSEITEN = {"seiten/erste-mannschaft.html": "1. Mannschaft", "seiten/zweite-mannschaft.html": "2. Mannschaft"}
KURZTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]


def naechste_spiele_liste(spiele, label, anzahl=6):
    e = lambda s: html.escape(s, quote=True)
    teile = []
    for z in [z for z in spiele if z["label"] == label and not z.get("abgesetzt")][:anzahl]:
        d = datetime.date.fromisoformat(z["datum"])
        heim = ist_sch(z["heim"])
        marke = '<em class="tm-marke">Heimspiel</em>' if heim else '<em class="tm-marke aus">Auswärts</em>'
        link = (f'<a href="{e(z["spiel"])}">Zum Spiel<span class="tm-sr"> {e(z["heim"])} gegen {e(z["gast"])}</span></a>'
                if z["spiel"] else "")
        teile.append(f'<li class="tm-spiel{" heim" if heim else ""}"><span class="tm-zeit">{z["zeit"]}</span>'
                     f'<span class="tm-team"><b>{KURZTAGE[d.weekday()]}, {d.day:02d}.{d.month:02d}.</b><small>{e(z["wettbewerb"])}</small></span>'
                     f'<span class="tm-paar"><span class="tm-gegner"><span>{e(z["heim"])}</span><i aria-hidden="true">:</i>'
                     f'<span>{e(z["gast"])}</span></span></span><span class="tm-info">{marke}{link}</span></li>')
    return '<ul class="tm-liste">' + "".join(teile) + "</ul>"


def aktualisiere_mannschaftsseiten(spiele):
    """„Nächste Spiele“ auf den Mannschaftsseiten aus den Terminen erneuern. Gibt die geänderten Dateien zurück."""
    geaendert = []
    for datei, label in MANNSCHAFTSSEITEN.items():
        pfad = os.path.join(REPO, datei)
        if not os.path.exists(pfad):
            continue
        t = open(pfad, encoding="utf-8").read()
        k = t.find("<h2>Nächste Spiele</h2>")
        a = t.find('<ul class="tm-liste">', k)
        b = t.find("</ul>", a)
        if k < 0 or a < 0 or b < 0:
            continue
        liste = naechste_spiele_liste(spiele, label)
        if liste == '<ul class="tm-liste"></ul>':
            continue  # nichts gefunden: alte Liste lieber stehen lassen
        neu = t[:a] + liste + t[b + 5:]
        if neu != t:
            open(pfad, "w", encoding="utf-8").write(neu)
            geaendert.append(datei)
    return geaendert


def baue(heute=None):
    heute = heute or datetime.date.today().isoformat()
    alt = open(SEITE, encoding="utf-8").read()
    bekannt = alte_bezeichnungen(alt)
    # Ab 60 Tagen zurück: verlegte Spiele stehen bei fussball.de unter ihrem ursprünglichen Datum
    von = (datetime.date.fromisoformat(heute) - datetime.timedelta(days=60)).isoformat()
    zeilen = spielplan(von, saisonende(heute))
    if not zeilen:
        sys.exit("Keine Spiele von fussball.de erhalten – Seite bleibt unverändert.")
    # Mannschaft (fussball.de team-id) -> Bezeichnung, gelernt aus Spielen, die schon auf der Seite stehen
    nach_team = {}
    for z in zeilen:
        b = bekannt.get(spiel_id(z["spiel"]))
        if b:
            url = z["heim_url"] if ist_sch(z["heim"]) else z["gast_url"]
            nach_team.setdefault(team_id(url), b)
    spiele = []
    for z in zeilen:
        if z["info"].lower() == "spielfrei" or not (ist_sch(z["heim"]) or ist_sch(z["gast"])):
            continue
        neu = re.match(r"(\d{2})\.(\d{2})\.(\d{4}) (\d{2}:\d{2})", z["info"])
        if neu:  # verlegt: am neuen Termin zeigen
            z["datum"], z["zeit"], z["verlegt"] = f"{neu.group(3)}-{neu.group(2)}-{neu.group(1)}", neu.group(4), True
        if z["info"].lower().startswith("absetz") or "abgesetzt" in z["info"].lower():
            z["abgesetzt"] = True
        if z["datum"] < heute:
            continue
        sch_name = z["heim"] if ist_sch(z["heim"]) else z["gast"]
        z["label"] = bezeichnung(z, sch_name, nach_team)
        spiele.append(z)
    # Doppelte weg: ein verlegtes Spiel steht am alten Datum (mit Hinweis) und am neuen Termin;
    # Turniere teilen sich eine Spiel-Nummer, deshalb gehören die Mannschaften zum Schlüssel.
    einmal = {}
    for z in spiele:
        k = (spiel_id(z["spiel"]), z["heim"], z["gast"]) if z["spiel"] else (z["datum"], z["zeit"], z["heim"], z["gast"])
        if k not in einmal:
            einmal[k] = z
        elif einmal[k].get("verlegt") and not z.get("verlegt"):
            z["verlegt"] = True  # Eintrag am neuen Termin nehmen, Hinweis „verlegt“ behalten
            einmal[k] = z
        elif z.get("verlegt"):
            einmal[k]["verlegt"] = True
    spiele = sorted(einmal.values(), key=lambda z: (z["datum"], z["zeit"]))

    wanderungen = wandertermine(heute)
    termine = sorted([(z["datum"], z["zeit"], 0, eintrag(z, z["label"])) for z in spiele]
                     + [(w["datum"], w["zeit"], 1, wander_eintrag(w)) for w in wanderungen]
                     + [(s["datum"], s["zeit"], 2, dart_eintrag(s)) for s in dartspiele(heute)])
    teile, tag = [], None
    for datum, _, _, li in termine:
        if datum != tag:
            if tag:
                teile.append("</ul></section>\n")
            tag = datum
            teile.append(tag_kopf(tag))
        teile.append(li + "\n")
    if tag:
        teile.append("</ul></section>\n")

    a = alt.find('<section class="tm-tag"')
    b = alt.find('<p class="tm-leer"')
    if a < 0 or b < 0:
        sys.exit("Aufbau der Termine-Seite nicht erkannt – Seite bleibt unverändert.")
    neu_liste = "".join(teile)

    # Abgleich: was ist neu, geändert, gestrichen, vorbei?
    vorher, nachher = eintraege_der_seite(alt[a:b]), eintraege_der_seite(neu_liste)
    noch_kommend = {k: v for k, v in vorher.items() if tag_iso(v) >= heute}
    if len(noch_kommend) >= 20 and len(nachher) < len(noch_kommend) * 0.6:
        sys.exit(f"fussball.de liefert nur {len(nachher)} statt bisher {len(noch_kommend)} kommender Spiele – "
                 "vermutlich eine Störung, Seite bleibt unverändert.")
    neu_k = [nachher[k] for k in nachher if k not in vorher]
    weg_k = [vorher[k] for k in vorher if k not in nachher and tag_iso(vorher[k]) >= heute]
    vorbei = [k for k in vorher if k not in nachher and tag_iso(vorher[k]) < heute]
    anders = [f"{vorher[k]}  →  {nachher[k]}" for k in nachher if k in vorher and vorher[k] != nachher[k]]
    seiten = aktualisiere_mannschaftsseiten(spiele)
    if seiten:
        print("„Nächste Spiele“ erneuert: " + ", ".join(seiten))
    if neu_liste == alt[a:b]:
        print("Keine Änderungen an den Terminen.")
        if seiten and os.environ.get("TERMINE_BERICHT"):
            open(os.environ["TERMINE_BERICHT"], "w", encoding="utf-8").write(
                "Naechste Spiele auf den Mannschaftsseiten aktualisiert\n\n" + "\n".join(seiten) + "\n")
        return []
    bericht = [f"{len(neu_k)} neu, {len(anders)} geändert, {len(weg_k)} gestrichen, {len(vorbei)} vorbei"]
    bericht += [f"+ {x}" for x in neu_k] + [f"~ {x}" for x in anders] + [f"- {x}" for x in weg_k]
    print("\n".join(bericht))

    neu_seite = alt[:a] + neu_liste + alt[b:]
    neu_seite = re.sub(r"Stand \d{2}\.\d{2}\.\d{4}", "Stand " + datetime.date.fromisoformat(heute).strftime("%d.%m.%Y"), neu_seite)
    neu_seite = neu_seite.replace("Alle Spiele unserer Mannschaften bis Jahresende", "Alle Spiele unserer Mannschaften bis Saisonende")
    neu_seite = neu_seite.replace("gibt es bis Jahresende keine Spiele", "gibt es bis Saisonende keine Spiele")
    open(SEITE, "w", encoding="utf-8").write(neu_seite)
    print(f"{len(spiele)} Spiele an {len({z['datum'] for z in spiele})} Tagen, "
          f"{sum(1 for z in spiele if z.get('verlegt'))} verlegt, {sum(1 for z in spiele if z.get('abgesetzt'))} abgesetzt, "
          f"{len(wanderungen)} Wanderungen, {len(dartspiele(heute))} Dartspiele.")
    # Für den täglichen Abgleich: Kurzbericht als Commit-Text
    if os.environ.get("TERMINE_BERICHT"):
        open(os.environ["TERMINE_BERICHT"], "w", encoding="utf-8").write(
            f"Termine abgeglichen: {bericht[0]}\n\n" + "\n".join(bericht[1:40]) + "\n")
    return spiele


if __name__ == "__main__":
    baue()
