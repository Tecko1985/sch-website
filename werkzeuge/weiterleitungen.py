#!/usr/bin/env python3
"""Weiterleitungen von den Adressen der alten Vereinsseite (WordPress) auf die neue Seite.

Aufruf (im Repo-Ordner, braucht Netz):
    python werkzeuge/weiterleitungen.py              schreibt .htaccess im Repo
    python werkzeuge/weiterleitungen.py <datei>      schreibt dorthin (umzug.py: in den Bauordner)

Schreibt .htaccess (Apache, für den Webspace bei Hetzner): jede alte Adresse eines Beitrags oder
einer Seite zeigt mit 301 ("dauerhaft umgezogen") auf die passende neue Seite. So landen alte Links
und Google-Treffer nach dem Umzug nicht auf "Seite nicht gefunden".
- Beitrag schon übernommen (seiten/beitrag-<slug>.html)  -> dorthin
- Beitrag liegt als Redaktionsbeitrag vor (gleicher Titel, Datum +-1 Tag) -> auf den Redaktionsbeitrag
- sonst -> News-Liste
- Seiten über die Linkkarte des Seitenbaus bzw. gleichen Dateinamen, sonst -> Startseite
Erst nach dem Umzug aktiv: auf GitHub Pages wird .htaccess nicht ausgewertet.
Nach neuen Beiträgen oder Seiten einfach neu laufen lassen.
"""
import datetime
import glob
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALT = "https://www.sc1911-heiligenstadt.de"
UA = {"User-Agent": "SCH-Website"}
ZIEL = os.path.join(REPO, ".htaccess")
UMZUG_2025 = os.path.join(os.path.dirname(REPO), "_umzug", "beitraege-2025")

# Alte Seiten, deren neue Datei anders heißt als der WordPress-Slug (zusätzlich zur Linkkarte)
SEITEN_FEST = {
    "impressum-2": "seiten/impressum.html",
    "datenschutz": "seiten/datenschutz.html",
    "news": "seiten/news.html",
    "anmelden": "seiten/login.html",  # WordPress-Login -> Login-Auswahl (seit 18.11.2026; auf dem Server von Hand: R=302)
    "startseite": "",
    "home": "",
}
# Beiträge mit eigener neuer Seite unter anderem Namen (Slug -> Redaktionsdatei bzw. Seite)
BEITRAEGE_FEST = {
    "ende-im-achtelfinale-2": "spielbericht-erfurt.html",
    "weiter-gehts": "inhalte/beitraege/*-erst-geduld-*.json",  # heißt in der Redaktion „Erst Geduld, dann ein Torfestival …“
}


# Steht oben in der .htaccess (Live-Prüfung 17.11.2026). Seit dem Umzug läuft dieses Skript nicht mehr
# (das alte WordPress fehlt); die .htaccess auf dem Server ist die echte und wird von Hand gepflegt.
SERVER_BLOCK = r"""
# --- Adresse, Fehlerseite, Schutz, Tempo (Live-Prüfung 17.11.2026, L-1/L-2/L-4/L-5/P-1/P-2) ---
# Immer verschlüsselt und immer mit www (eine Adresse für Google, Redaktion und Browser-Speicher)
RewriteEngine On
RewriteCond %{HTTPS} !=on [OR]
RewriteCond %{HTTP_HOST} !^www\. [NC]
RewriteRule ^ https://www.sc1911-heiligenstadt.de%{REQUEST_URI} [R=301,L,NE]
ErrorDocument 404 /404.html
<IfModule mod_headers.c>
Header always set Strict-Transport-Security "max-age=31536000" "expr=%{HTTPS} == 'on'"
Header always set X-Content-Type-Options "nosniff"
Header always set Referrer-Policy "strict-origin-when-cross-origin"
Header always set X-Frame-Options "SAMEORIGIN"
</IfModule>
<IfModule mod_deflate.c>
AddOutputFilterByType DEFLATE text/html text/css text/javascript application/javascript application/json image/svg+xml application/xml text/xml text/plain
</IfModule>
# Kurz genug, dass neue Fassungen ohne ?v= (z. B. neu.js) am selben Tag ankommen
<IfModule mod_expires.c>
ExpiresActive On
ExpiresByType text/html "access plus 0 seconds"
ExpiresByType text/css "access plus 1 hour"
ExpiresByType text/javascript "access plus 1 hour"
ExpiresByType application/javascript "access plus 1 hour"
ExpiresByType application/json "access plus 1 hour"
ExpiresByType image/webp "access plus 7 days"
ExpiresByType image/jpeg "access plus 7 days"
ExpiresByType image/png "access plus 7 days"
ExpiresByType image/svg+xml "access plus 7 days"
ExpiresByType font/woff2 "access plus 30 days"
ExpiresByType font/woff "access plus 30 days"
ExpiresByType application/pdf "access plus 1 day"
</IfModule>
# --- Ende ---
"""


def hole_alle(art, felder):
    alle, seite = [], 1
    while True:
        url = f"{ALT}/wp-json/wp/v2/{art}?per_page=100&page={seite}&_fields={felder}"
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                teil = json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code == 400:
                break
            raise
        if not teil:
            break
        alle += teil
        seite += 1
    return alle


def schluessel(titel):
    return re.sub(r"[^a-z0-9äöüß]", "", html.unescape(re.sub(r"<[^>]+>", "", titel)).lower())


def pfad(link):
    """https://www.sc1911-heiligenstadt.de/2026/10/04/slug/ -> 2026/10/04/slug (ohne Schrägstriche, dekodiert)"""
    return urllib.parse.unquote(urllib.parse.urlparse(link).path).strip("/")


def redaktion():
    """[(datum, titel-schlüssel, seite)] der Redaktionsbeiträge"""
    aus = []
    for f in glob.glob(os.path.join(REPO, "inhalte/beitraege/*.json")):
        d = json.load(open(f, encoding="utf-8"))
        aus.append((d.get("datum", ""), schluessel(d.get("titel", "")), f"seiten/beitrag-{os.path.basename(f)[:-5]}.html", os.path.basename(f)))
    return aus


def dokumente():
    """Regeln für alte Datei-Adressen: jedes PDF aus assets/dokumente/ unter seinem WordPress-Pfad
    wp-content/uploads/<Jahr>/<Monat>/<Name> (Bugjagd 16.11.2026 H2-6: Flyer/QR-Codes/Mails)."""
    aus = []
    for f in sorted(glob.glob(os.path.join(REPO, "assets", "dokumente", "*"))):
        name = os.path.basename(f)
        aus.append(f"RewriteRule ^wp-content/uploads/[0-9]{{4}}/[0-9]{{2}}/{re.escape(name)}$ /assets/dokumente/{name} [R=301,L]")
    return aus


def main():
    # Beiträge aus 2025 liegen bis zum Umzug außerhalb des (öffentlichen) Repos, siehe UMZUG.md
    da = lambda p: any(os.path.isfile(os.path.join(w, p)) for w in (REPO, UMZUG_2025))
    regeln, fehlend = {}, []
    red = redaktion()

    for p in hole_alle("posts", "slug,link,date,title"):
        ziel = f"seiten/beitrag-{p['slug']}.html"
        fest = BEITRAEGE_FEST.get(p["slug"], "")
        if fest.startswith("inhalte/"):
            datei = glob.glob(os.path.join(REPO, fest))
            fest = f"seiten/beitrag-{os.path.basename(datei[0])[:-5]}.html" if datei else ""
        if fest:
            ziel = fest
        elif not da(ziel):
            # Redaktionsseiten entstehen erst beim Pages-Bau – nicht auf der Platte suchen
            tag = datetime.date.fromisoformat(p["date"][:10])
            nah = {str(tag + datetime.timedelta(days=d)) for d in range(-3, 4)}
            k = schluessel(p["title"]["rendered"])
            treffer = [s for (dt, sk, s, _) in red if dt in nah and sk and (sk in k or k in sk)]
            ziel = treffer[0] if treffer else "seiten/news.html"
            if not treffer:
                fehlend.append(p["slug"])
        regeln[pfad(p["link"])] = ziel

    karte = {}
    lk = os.path.join(REPO, "werkzeug", "linkkarte.json")
    if os.path.exists(lk):
        for url, datei in json.load(open(lk, encoding="utf-8")).items():
            if not datei.startswith(("beitrag-", "..")):
                karte[pfad(url)] = "seiten/" + datei
    for s in hole_alle("pages", "slug,link"):
        alt = pfad(s["link"])
        if not alt:
            continue  # die Startseite selbst
        if s["slug"] in SEITEN_FEST:
            ziel = SEITEN_FEST[s["slug"]]
        elif alt in karte and da(karte[alt]):
            ziel = karte[alt]
        elif da(f"seiten/{s['slug']}.html"):
            ziel = f"seiten/{s['slug']}.html"
        else:
            ziel = ""
        regeln[alt] = ziel

    zeilen = [
        "# Erzeugt von werkzeuge/weiterleitungen.py – nicht von Hand ändern, neu erzeugen.",
        "# Alte Adressen der WordPress-Seite -> neue Seite (301 = dauerhaft umgezogen).",
        "# Wirkt erst auf dem Webspace (Apache), auf GitHub Pages nicht.",
        *SERVER_BLOCK.splitlines(),
        "RewriteEngine On",
        "",
        "# Kategorien, Schlagworte, Feeds und Seitenzahlen der News -> News-Liste",
        r"RewriteRule ^(category|tag|author)/ /seiten/news.html [R=301,L]",
        r"RewriteRule ^(feed|comments/feed)/?$ /seiten/news.html [R=301,L]",
        r"RewriteRule ^page/[0-9]+/?$ /seiten/news.html [R=301,L]",
        "# Beiträge bis Juni 2025 (nur noch im Nextcloud-Archiv) -> News-Archiv",
        r"RewriteRule ^(2021|2022|2023|2024)/[0-9]{2}/[0-9]{2}/ /seiten/archiv.html [R=301,L]",
        r"RewriteRule ^2025/0[1-6]/[0-9]{2}/ /seiten/archiv.html [R=301,L]",
        "# Dokumente (PDF) der alten Seite -> assets/dokumente/",
        *dokumente(),
        "",
    ]
    for alt in sorted(regeln):
        ziel = regeln[alt] if regeln[alt].startswith("https://") else "/" + regeln[alt]
        zeilen.append(f"RewriteRule ^{re.escape(alt)}/?$ {ziel} [R=301,L]")
    ziel = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else ZIEL
    open(ziel, "w", encoding="utf-8", newline="\n").write("\n".join(zeilen) + "\n")
    print(f"{len(regeln)} Weiterleitungen in {ziel}")
    if fehlend:
        print(f"{len(fehlend)} Beiträge ohne eigene neue Seite (zeigen auf die News-Liste): {', '.join(fehlend[:10])}")


if __name__ == "__main__":
    main()
