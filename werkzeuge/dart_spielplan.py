"""Spielplan der Carrot Kings (Dart) in seiten/dart.html einbauen (zwischen <!--dartplan--> … <!--/dartplan-->).

Die Spiele stehen unten in PLAN: (H/A, Gegner, Datum, verlegt?). Nach einer Änderung:
    python3 werkzeuge/dart_spielplan.py
Die Termine-Seite liest die Spiele beim täglichen Abgleich aus seiten/dart.html (werkzeuge/termine.py).
Die Paarung steht immer mit der Heimmannschaft zuerst.
"""
import datetime, html, os, re

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIR = "Carrot Kings"
ORT_HEIM = "Gastwirtschaft „Schwarzer Adler“, Heiligenstadt"
TAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
PLAN = {
    "1. Mannschaft": [
        ("A", "Tigers Birkungen I", "24.10.2026", True), ("H", "Red Devils Uder I", "06.11.2026", True),
        ("A", "Bulls Geisleden I", "31.10.2026", False), ("H", "Bulls Geisleden II", "28.11.2026", False),
        ("A", "Eisbären Kaltohmfeld I", "19.12.2026", False),
        ("H", "Tigers Birkungen I", "30.01.2027", False), ("A", "Red Devils Uder I", "27.02.2027", False),
        ("H", "Bulls Geisleden I", "27.03.2027", False), ("A", "Bulls Geisleden II", "24.04.2027", False),
        ("H", "Eisbären Kaltohmfeld I", "08.05.2027", False)],
    "2. Mannschaft": [
        ("A", "Grashoppers Teistungen II", "29.08.2026", False), ("A", "Red Devils Uder II", "26.09.2026", False),
        ("H", "Ohmfelder Luchse", "31.10.2026", False), ("A", "Tigers Birkungen III", "28.11.2026", False),
        ("H", "Steelravens Hüpstedt I", "19.12.2026", False),
        ("H", "Grashoppers Teistungen II", "30.01.2027", False), ("H", "Red Devils Uder II", "27.02.2027", False),
        ("A", "Ohmfelder Luchse", "27.03.2027", False), ("H", "Tigers Birkungen III", "24.04.2027", False),
        ("A", "Steelravens Hüpstedt I", "08.05.2027", False)],
    "Kidsliga": [
        ("H", "Bulls Juniors Geisleden", "05.09.2026", False), ("H", "Yung Devilz Uder", "07.11.2026", False),
        ("A", "Bulls Juniors Geisleden", "12.12.2026", False), ("A", "Yung Devilz Uder", "06.02.2027", False)],
}
e = lambda s: html.escape(s, quote=True)


def zeile(nr, team, art, gegner, datum, verlegt):
    d = datetime.datetime.strptime(datum, "%d.%m.%Y").date()
    heim = art == "H"
    h, g = (WIR, gegner) if heim else (gegner, WIR)   # Heimmannschaft immer zuerst
    return (f'<li class="dp-spiel{" heim" if heim else ""}" data-datum="{d.isoformat()}" data-zeit="14:00" '
            f'data-team="{e(team)}" data-heim="{1 if heim else 0}" data-gegner="{e(gegner)}">'
            f'<span class="dp-nr">{nr:02d}</span>'
            f'<time class="dp-datum" datetime="{d.isoformat()}T14:00"><b>{TAGE[d.weekday()]}, {d.day:02d}.{d.month:02d}.</b>'
            f'<small>{d.year} · 14:00 Uhr</small></time>'
            f'<span class="dp-paar"><span{" class=dp-wir" if heim else ""}>{e(h)}</span><i aria-hidden="true">:</i>'
            f'<span{"" if heim else " class=dp-wir"}>{e(g)}</span></span>'
            f'<em class="dp-marke{"" if heim else " aus"}">{"Heim" if heim else "Auswärts"}'
            f'{" · verlegt" if verlegt else ""}</em></li>')


teile = ['<!--dartplan--><section class="dp-plan" id="spielplan" aria-labelledby="dp-titel"><div class="dk-kopf">'
         '<h2 id="dp-titel">Spielplan 2026/27</h2><span>Alle Spiele um 14:00 Uhr</span></div>']
for team, spiele in PLAN.items():
    teile.append(f'<h3 class="dp-team">{e(team)} <small>{len(spiele)} Spieltage</small></h3>')
    for runde, von, bis in (("Hinrunde", 0, len(spiele) // 2), ("Rückrunde", len(spiele) // 2, len(spiele))):
        teile.append(f'<h4 class="dp-runde">{runde}</h4><ol class="dp-liste">')
        teile += [zeile(i + 1, team, *spiele[i]) for i in range(von, bis)]
        teile.append("</ol>")
teile.append(f'<p class="dp-hinweis">Heimspiele in der {e(ORT_HEIM)}. „Verlegt“: neuer Termin laut Spielplan.</p>'
             '</section><script>(function(){var h=new Date();h=h.getFullYear()+"-"+("0"+(h.getMonth()+1)).slice(-2)+"-"+("0"+h.getDate()).slice(-2);'
             'document.querySelectorAll(".dp-spiel").forEach(function(l){if(l.getAttribute("data-datum")<h)l.classList.add("vorbei")})})()</script>'
             '<!--/dartplan-->')
block = "".join(teile)

p = f"{REPO}/seiten/dart.html"
t = open(p, encoding="utf-8").read()
if "<!--dartplan-->" in t:
    t = re.sub(r"<!--dartplan-->.*?<!--/dartplan-->", lambda m: block, t, count=1, flags=re.S)
else:
    assert t.count("<!--dartkader-->") == 1
    t = t.replace("<!--dartkader-->", block + "<!--dartkader-->", 1)
open(p, "w", encoding="utf-8").write(t)
print("ok", sum(len(v) for v in PLAN.values()), "Spiele")
