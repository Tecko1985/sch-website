#!/usr/bin/env python3
"""Eigene Suche der Vereinsseite (ersetzt die WordPress-Suche ?s=).

    python werkzeuge/suche.py seite          schreibt seiten/suche.html (Suchseite, im Repo)
    python werkzeuge/suche.py index _site    schreibt _site/suche-index.json (beim Pages-Bau,
                                             nach beitraege.py, damit Redaktionsbeiträge drin sind)

Die Suche läuft ganz im Browser: suche.html lädt suche-index.json vom eigenen Server und
filtert dort. Keine Anfrage an fremde Dienste, keine Cookies.
"""
import glob
import html
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VORLAGE = "seiten/datenschutz.html"
AUSLASSEN = {"suche.html", "news.html", "datenschutz-neu.html"}
TEXTLAENGE = 700


def text_aus(s):
    s = re.sub(r"<(script|style)\b.*?</\1>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def eintrag(pfad, rel):
    s = open(pfad, encoding="utf-8", errors="replace").read()
    held = re.search(r'<div class="sch-reporthero[^"]*">(.*?)</div></div>', s, re.S)
    titel = kicker = datum = ""
    if held:
        m = re.search(r"<h1>(.*?)</h1>", held.group(1), re.S)
        titel = text_aus(m.group(1)) if m else ""
        m = re.search(r"<span>(.*?)</span>", held.group(1), re.S)
        kicker = text_aus(m.group(1)) if m else ""
        m = re.search(r'<p class="sp-datum">(\d\d)\.(\d\d)\.(\d{4})', held.group(1))
        datum = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else ""
    if not titel:
        m = re.search(r"<title>(.*?)</title>", s, re.S)
        titel = text_aus(m.group(1)).split(" · ")[0] if m else rel
    if not datum:  # Spielberichte u. a. ohne sp-datum: Datum steckt im Dateinamen (beitrag-2026-11-13-…)
        m = re.match(r"beitrag-(\d{4}-\d{2}-\d{2})-", os.path.basename(pfad))
        datum = m.group(1) if m else ""
    art = re.search(r"<article\b[^>]*>(.*?)</article>", s, re.S) or re.search(r"<main\b[^>]*>(.*?)</main>", s, re.S)
    text = text_aus(art.group(1)) if art else ""
    return {"u": rel, "t": titel, "k": kicker, "d": datum, "x": text[:TEXTLAENGE]}


def index(ziel):
    eintraege = []
    for pfad in sorted(glob.glob(os.path.join(ziel, "seiten", "*.html"))):
        name = os.path.basename(pfad)
        if name in AUSLASSEN:
            continue
        eintraege.append(eintrag(pfad, "seiten/" + name))
    with open(os.path.join(ziel, "suche-index.json"), "w", encoding="utf-8", newline="\n") as f:
        json.dump(eintraege, f, ensure_ascii=False, separators=(",", ":"))
    print(f"suche-index.json: {len(eintraege)} Seiten, {os.path.getsize(os.path.join(ziel, 'suche-index.json')) // 1024} KB")


SUCHSEITE = """
<p class="fb-lead">Durchsucht alle Seiten und Beiträge des SCH.</p>
<form class="su-form" role="search" action="suche.html" method="get">
<label for="su-feld">Suchbegriff</label>
<div class="su-zeile"><input id="su-feld" name="q" type="search" autocomplete="off" placeholder="z. B. Pokal, U17, Mitglied werden"><button type="submit">Suchen</button></div>
</form>
<p class="su-status" id="su-status" role="status" aria-live="polite"></p>
<ol class="su-treffer" id="su-treffer"></ol>
<noscript><p>Die Suche braucht JavaScript. Alle Beiträge findet ihr auch unter <a href="news.html">News</a>.</p></noscript>
<style>
.su-form label{display:block;font-weight:700;margin:0 0 6px}
.su-zeile{display:flex;gap:8px;flex-wrap:wrap}
.su-zeile input{flex:1 1 220px;min-height:48px;padding:10px 14px;font-size:17px;border:2px solid #1b2d4f;border-radius:10px}
.su-zeile button{min-height:48px;padding:0 22px;border:0;border-radius:10px;background:#1b2d4f;color:#fff;font-weight:700;font-size:16px;cursor:pointer}
.su-status{margin:18px 0 6px;font-weight:700}
.su-treffer{list-style:none;padding:0;margin:0}
.su-treffer li{border-top:1px solid #d7dce4;padding:14px 0}
.su-treffer a{font-weight:700;font-size:18px;color:#1b2d4f}
.su-treffer small{display:block;color:#5a6577;margin:2px 0 4px}
.su-treffer mark{background:#aac7ed80;color:inherit;padding:0 2px;border-radius:3px}
</style>
<script>
(function () {
  var feld = document.getElementById('su-feld'), status = document.getElementById('su-status'), liste = document.getElementById('su-treffer');
  var q = (new URLSearchParams(location.search).get('q') || '').trim();
  feld.value = q;
  if (!q) { feld.focus(); return; }
  var norm = function (s) { return String(s || '').toLowerCase().normalize('NFD').replace(/[\\u0300-\\u036f]/g, '').replace(/ß/g, 'ss'); };
  var worte = norm(q).split(/\\s+/).filter(Boolean);
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]; }); };
  status.textContent = 'Suche …';
  fetch('../suche-index.json').then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (alle) {
    var treffer = alle.map(function (e) {
      var t = norm(e.t), x = norm(e.x), punkte = 0;
      for (var i = 0; i < worte.length; i++) {
        var w = worte[i];
        if (t.indexOf(w) >= 0) punkte += 10; else if (x.indexOf(w) >= 0 || norm(e.k).indexOf(w) >= 0) punkte += 1; else return null;
      }
      return { e: e, p: punkte };
    }).filter(Boolean).sort(function (a, b) { return b.p - a.p || (b.e.d || '').localeCompare(a.e.d || ''); }).slice(0, 50);
    status.textContent = treffer.length ? treffer.length + (treffer.length === 50 ? '+' : '') + ' Treffer für „' + q + '“' : 'Nichts gefunden für „' + q + '“. Probier ein anderes Wort.';
    liste.innerHTML = treffer.map(function (t) {
      var e = t.e, x = e.x, n = norm(x), pos = n.indexOf(worte[0]);
      var start = Math.max(0, pos - 60), stueck = (start ? '… ' : '') + x.slice(start, start + 200) + (x.length > start + 200 ? ' …' : '');
      var hell = esc(stueck);
      // Umlaute und ß wie beim Suchen gleich behandeln: "fussball" markiert auch "Fußball"
      var muster = function (w) { return w.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&').replace(/ss/g, '(?:ss|ß)').replace(/a/g, '[aä]').replace(/o/g, '[oö]').replace(/u/g, '[uü]'); };
      worte.forEach(function (w) { if (w.length > 1) hell = hell.replace(new RegExp('(' + muster(w) + ')', 'gi'), '<mark>$1</mark>'); });
      var datum = e.d ? e.d.split('-').reverse().join('.') : '';
      return '<li><a href="../' + esc(e.u) + '">' + esc(e.t) + '</a><small>' + esc([e.k, datum].filter(Boolean).join(' · ')) + '</small><span>' + hell + '</span></li>';
    }).join('');
  }).catch(function () { status.textContent = 'Die Suche ist gerade nicht verfügbar. Alle Beiträge findet ihr unter News.'; });
})();
</script>
"""


def seite():
    vorlage = open(os.path.join(REPO, VORLAGE), encoding="utf-8").read()
    t = re.sub(r"<title>.*?</title>", "<title>Suche · 1. SC 1911 Heiligenstadt</title>", vorlage, count=1, flags=re.S)
    t = re.sub(r'(<meta name="description" content=")[^"]*', lambda m: m.group(1) + "Alle Seiten und Beiträge des 1. SC 1911 Heiligenstadt durchsuchen.", t, count=1)
    t = re.sub(r'(<meta property="og:title" content=")[^"]*', lambda m: m.group(1) + "Suche · 1. SC 1911 Heiligenstadt", t, count=1)
    t = re.sub(r'(<meta property="og:url" content="[^"]*/)seiten/[^"]*', lambda m: m.group(1) + "seiten/suche.html", t, count=1)
    held = '<div class="sch-reporthero sp-held"><img src="../assets/hero.jpg" alt=""><div><span>Suche</span><h1>Suche</h1></div></div>'
    main = f'<main class="sch-report sp-seite">{held}<article class="sp-inhalt">\n{SUCHSEITE.strip()}\n</article>'
    t, n = re.subn(r'<main class="sch-report sp-seite">.*?</article>', lambda m: main, t, count=1, flags=re.S)
    if n != 1:
        raise SystemExit("Vorlage ohne <main class=\"sch-report sp-seite\">…</article>")
    with open(os.path.join(REPO, "seiten", "suche.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(t)
    print("seiten/suche.html")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "seite":
        seite()
    elif len(sys.argv) >= 3 and sys.argv[1] == "index":
        index(os.path.abspath(sys.argv[2]))
    else:
        sys.exit(__doc__)
