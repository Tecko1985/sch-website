#!/usr/bin/env python3
"""Baut umzug.html: Platzhalter "Wir ziehen um" fuer die Zeit des Webseiten-Umzugs.

Aufruf:  python werkzeuge/umzug_seite.py
Eine einzige Datei: Logo und Schrift stecken als data:-Adresse drin, damit sie auf
jeden Webspace passt (auch als index.html) und nichts von fremden Servern laedt.
Impressum nach der Vereinsseite (Stand WordPress 06.04.2026).
"""
import base64
import io
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def data(pfad, typ):
    with open(os.path.join(REPO, pfad), "rb") as f:
        return f"data:{typ};base64," + base64.b64encode(f.read()).decode("ascii")


def logo_klein():
    # Wappen auf 240 px Hoehe (reicht fuer 104 px Anzeige auch auf Retina-Handys)
    from PIL import Image
    im = Image.open(os.path.join(REPO, "assets/logo.png"))
    im = im.resize((round(im.width * 240 / im.height), 240), Image.LANCZOS)
    puffer = io.BytesIO()
    im.save(puffer, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(puffer.getvalue()).decode("ascii")


LOGO = logo_klein()
SCHRIFT = data("assets/barlow.woff", "font/woff")

SEITE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex">
<meta name="theme-color" content="#1b2d4f">
<title>Wir ziehen um · 1. SC 1911 Heiligenstadt</title>
<link rel="icon" href="__LOGO__">
<style>
@font-face{font-family:'SCH Barlow';src:url(__SCHRIFT__) format('woff');font-weight:700;font-display:swap}
:root{--navy:#1b2d4f;--tief:#0b1a38;--hell:#aac7ed;--weiss:#fff;--text:#dce3ef}
*{box-sizing:border-box}
html,body{margin:0;min-height:100%}
body{background:radial-gradient(120% 80% at 50% 0%,#24406e 0%,var(--navy) 45%,var(--tief) 100%) fixed;color:var(--text);font:17px/1.6 Arial,Helvetica,sans-serif;display:flex;flex-direction:column;align-items:center;padding:48px 16px 32px}
main{width:100%;max-width:860px;text-align:center}
.wappen{width:104px;height:auto;filter:drop-shadow(0 10px 24px #0008)}
.verein{margin:18px 0 0;font:700 15px Arial,sans-serif;letter-spacing:3px;text-transform:uppercase;color:var(--hell)}
h1{font:700 clamp(40px,8vw,72px)/1.02 'SCH Barlow',Impact,'Arial Narrow',sans-serif;text-transform:uppercase;color:var(--weiss);margin:18px 0 0}
.ball{display:inline-block;animation:rollen 3.2s ease-in-out infinite}
@keyframes rollen{0%,100%{transform:translateX(-6px) rotate(-20deg)}50%{transform:translateX(6px) rotate(20deg)}}
@media (prefers-reduced-motion:reduce){.ball{animation:none}}
.lead{font-size:19px;color:var(--text);max-width:560px;margin:20px auto 0}
.knoepfe{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:34px 0 0}
.knoepfe a{display:flex;align-items:center;justify-content:center;min-height:52px;padding:12px 16px;border-radius:12px;background:#ffffff14;border:1px solid #aac7ed40;color:var(--weiss);font-weight:700;text-decoration:none;transition:background .2s,transform .2s}
.knoepfe a:hover,.knoepfe a:focus-visible{background:#ffffff26;transform:translateY(-2px)}
.knoepfe a.haupt{background:var(--hell);color:var(--navy);border-color:var(--hell)}
a:focus-visible{outline:3px solid var(--hell);outline-offset:3px}
.kontakt{margin:34px auto 0;padding:20px;border-radius:14px;background:#0b1a3866;border:1px solid #aac7ed2e;max-width:560px}
.kontakt h2{font:700 22px 'SCH Barlow',Impact,sans-serif;text-transform:uppercase;color:var(--weiss);margin:0 0 6px}
.kontakt p{margin:0}
.kontakt a{color:var(--hell);font-weight:700}
footer{width:100%;max-width:720px;margin-top:40px;font-size:14px}
details{border-top:1px solid #aac7ed33;padding:6px 0}
summary{cursor:pointer;min-height:44px;display:flex;align-items:center;font-weight:700;color:var(--weiss)}
details p,details li{color:var(--text)}
details a{color:var(--hell)}
details ul{padding-left:20px;margin:6px 0}
</style>
</head>
<body>
<main>
<img class="wappen" src="__LOGO__" alt="Wappen des 1. SC 1911 Heiligenstadt" width="827" height="945">
<p class="verein">1. SC 1911 Heiligenstadt e.V.</p>
<h1>Wir ziehen um <span class="ball" aria-hidden="true">⚽</span></h1>
<p class="lead">Unsere Webseite bekommt gerade ein neues Zuhause. In Kürze sind wir hier wieder für euch am Ball – mit News, Spielen und allem rund um den Gesundbrunnen.</p>
<nav class="knoepfe" aria-label="Bis dahin erreicht ihr uns hier">
<a class="haupt" href="https://www.fussball.de/verein/1-sc-1911-heiligenstadt-thueringen/-/id/00ES8GNC5C0000A8VV0AG08LVUPGND5I">Spiele &amp; Ergebnisse</a>
<a href="https://www.instagram.com/sc1911heiligenstadt/">Instagram</a>
<a href="https://www.instagram.com/sc1911heiligenstadt_nachwuchs/">Instagram Nachwuchs</a>
<a href="https://www.facebook.com/1-SC-1911-Heiligenstadt-News-443349765710542/">Facebook</a>
</nav>
<section class="kontakt" aria-labelledby="kontakt">
<h2 id="kontakt">Kontakt zur Geschäftsstelle</h2>
<p><a href="mailto:info@sc1911-heiligenstadt.de">info@sc1911-heiligenstadt.de</a></p>
</section>
</main>
<footer>
<details>
<summary>Impressum</summary>
<p>1. SC 1911 Heiligenstadt e.V.<br>Leineberg 2<br>37308 Heilbad Heiligenstadt</p>
<p>Vertreten durch den Vorstand: Thadäus König, Manuel Lubojanski, Christoph Rodenstock, Sebastian Möhlhenrich, Michael Apel</p>
<p>Telefon: +49 3606 612202<br>Telefax: +49 3606 509091<br>E-Mail: <a href="mailto:info@sc1911-heiligenstadt.de">info@sc1911-heiligenstadt.de</a></p>
<p>Vereinsregister: Amtsgericht Heilbad Heiligenstadt, Vereinsregisternummer 400083<br>LSB-Nr.: 150004</p>
<p>Wir sind nicht bereit und nicht verpflichtet, an Streitbeilegungsverfahren vor einer Verbraucherschlichtungsstelle teilzunehmen.</p>
</details>
<details>
<summary>Datenschutz</summary>
<p>Diese Seite setzt keine Cookies, zählt keine Besucher und lädt nichts von anderen Anbietern. Beim Aufruf speichert der Webserver technisch nötige Daten (zum Beispiel IP-Adresse, Uhrzeit, aufgerufene Seite) für kurze Zeit in Protokolldateien. Das ist nötig, um die Seite sicher auszuliefern (Art. 6 Abs. 1 lit. f DSGVO).</p>
<p>Verantwortlich ist der 1. SC 1911 Heiligenstadt e.V. (Anschrift im Impressum). Ihr habt das Recht auf Auskunft, Berichtigung, Löschung, Einschränkung der Verarbeitung und Widerspruch sowie auf Beschwerde bei einer Datenschutz-Aufsichtsbehörde, in Thüringen beim TLfDI. Schreibt uns dazu an <a href="mailto:info@sc1911-heiligenstadt.de">info@sc1911-heiligenstadt.de</a>.</p>
<p>Klickt ihr auf Instagram, Facebook oder fussball.de, verlasst ihr diese Seite; dort gelten die Datenschutzhinweise der jeweiligen Anbieter.</p>
</details>
</footer>
</body>
</html>
"""

ziel = os.path.join(REPO, "umzug.html")
with open(ziel, "w", encoding="utf-8", newline="\n") as f:
    f.write(SEITE.replace("__LOGO__", LOGO).replace("__SCHRIFT__", SCHRIFT))
print(ziel, os.path.getsize(ziel) // 1024, "KB")
