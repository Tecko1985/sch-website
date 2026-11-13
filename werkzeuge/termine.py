"""Termine-Seite (seiten/termine.html) aus dem Vereinsspielplan auf fussball.de neu bauen.

Aufruf:  python3 werkzeuge/termine.py
Holt alle Spiele von heute bis Saisonende (mit Spielort), lässt spielfreie Termine weg,
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
SAISONENDE = "2027-06-30"
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


def tag_kopf(iso):
    d = datetime.date.fromisoformat(iso)
    wt, mo = TAGE[d.weekday()], MONATE[d.month - 1]
    return (f'<section class="tm-tag" aria-label="{wt}, {d.day}. {mo} {d.year}"><h2><span>{wt}</span> {d.day}. {mo}</h2>'
            f'<ul class="tm-liste">\n')


def baue(heute=None):
    heute = heute or datetime.date.today().isoformat()
    alt = open(SEITE, encoding="utf-8").read()
    bekannt = alte_bezeichnungen(alt)
    zeilen = spielplan(heute, SAISONENDE)
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
    spiele.sort(key=lambda z: (z["datum"], z["zeit"]))

    teile, tag = [], None
    for z in spiele:
        if z["datum"] != tag:
            if tag:
                teile.append("</ul></section>\n")
            tag = z["datum"]
            teile.append(tag_kopf(tag))
        teile.append(eintrag(z, z["label"]) + "\n")
    if tag:
        teile.append("</ul></section>\n")

    a = alt.find('<section class="tm-tag"')
    b = alt.find('<p class="tm-leer"')
    if a < 0 or b < 0:
        sys.exit("Aufbau der Termine-Seite nicht erkannt – Seite bleibt unverändert.")
    neu_seite = alt[:a] + "".join(teile) + alt[b:]
    neu_seite = re.sub(r"Stand \d{2}\.\d{2}\.\d{4}", "Stand " + datetime.date.fromisoformat(heute).strftime("%d.%m.%Y"), neu_seite)
    neu_seite = neu_seite.replace("Alle Spiele unserer Mannschaften bis Jahresende", "Alle Spiele unserer Mannschaften bis Saisonende")
    neu_seite = neu_seite.replace("gibt es bis Jahresende keine Spiele", "gibt es bis Saisonende keine Spiele")
    open(SEITE, "w", encoding="utf-8").write(neu_seite)
    print(f"{len(spiele)} Spiele an {len({z['datum'] for z in spiele})} Tagen, "
          f"{sum(1 for z in spiele if z.get('verlegt'))} verlegt, {sum(1 for z in spiele if z.get('abgesetzt'))} abgesetzt.")
    return spiele


if __name__ == "__main__":
    baue()
