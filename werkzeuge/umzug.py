#!/usr/bin/env python3
"""Umzug der Vereinsseite auf den Hetzner-Webspace – ein Befehl statt zehn Handgriffe.

    python werkzeuge/umzug.py probe          Generalprobe: komplette Seite nach /neu-probe/ (WordPress bleibt)
    python werkzeuge/umzug.py sichern        nur WordPress sichern (Datenbank + Dateien) nach _umzug/
    python werkzeuge/umzug.py echt --ja      DER Umzug: sichern, bauen, hochladen, WordPress beiseitelegen
    python werkzeuge/umzug.py zurueck --ja   Notfall: WordPress wieder an seinen Platz, neue Seite beiseite

Was "probe" und "echt" tun (siehe UMZUG.md):
 1. Seite bauen wie GitHub (Repo-Dateien, Redaktionsbeiträge, neu/, Suchindex), Instagram von der Vorschau
 2. Beiträge aus 2025 (../_umzug/beitraege-2025, nicht im öffentlichen Repo) dazu, Karten in die News
 3. Weiterleitungen alter WordPress-Adressen (.htaccess) frisch erzeugen
 4. Umzugs-Schalter (noindex raus, Domain, Datenschutz für Hetzner, robots.txt, sitemap.xml)
 5. Hochladen in einen Wartebereich außerhalb des Webordners, dann in Sekunden umschalten:
    der alte Inhalt wird nur VERSCHOBEN (nach ~/umzug-alt-…), nie gelöscht.
Die Probe trägt zusätzlich "noindex" im Kopf jeder Antwort, damit Google sie nicht aufnimmt.

Braucht den SSH-Schlüssel %USERPROFILE%\\.ssh\\sch_hetzner (öffentlicher Teil liegt auf dem Server).
Die Mails (vmail) und die Datenbank fasst das Skript nie an.
"""
import datetime
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UMZUG = os.path.join(os.path.dirname(REPO), "_umzug")
BEITRAEGE_2025 = os.path.join(UMZUG, "beitraege-2025")
DOMAIN = "https://www.sc1911-heiligenstadt.de/"
VORSCHAU = "https://tecko1985.github.io/sch-website/"
HOST = "sccnld@dedi1977.your-server.de"
SCHLUESSEL = os.path.join(os.path.expanduser("~"), ".ssh", "sch_hetzner")
WEBORDNER = "public_html"  # Verknüpfung auf /usr/www/users/sccnld, gleiches Dateisystem wie ~ (mv ist sofort)
WARTEN = "umzug-neu"       # im Home, außerhalb des Webordners
HEUTE = datetime.date.today().isoformat()


def ssh_befehl():
    exe = shutil.which("ssh") or "ssh"
    win = os.path.join(os.environ.get("WINDIR", ""), "System32", "OpenSSH", "ssh.exe")
    if os.path.isfile(win):
        exe = win  # Windows-SSH kennt den Host-Schlüssel aus %USERPROFILE%\.ssh\known_hosts
    return [exe, "-p", "222", "-i", SCHLUESSEL, "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", HOST]


def ssh(befehl, daten=None, ausgabe=None):
    r = subprocess.run(ssh_befehl() + [befehl], input=daten, stdout=ausgabe or subprocess.PIPE)
    if r.returncode != 0:
        sys.exit(f"Abbruch: Befehl auf dem Server fehlgeschlagen ({r.returncode}): {befehl[:80]}")
    return r.stdout.decode("utf-8", "replace") if ausgabe is None and r.stdout else ""


def schritt(text):
    print(f"\n== {text}", flush=True)


# ---------------------------------------------------------------- sichern
DBDUMP_PHP = r"""<?php
// DB-Zugang aus wp-config.php lesen (nie ausgeben), Dump nach stdout.
$c = file_get_contents('wp-config.php'); $w = [];
foreach (['DB_NAME','DB_USER','DB_PASSWORD','DB_HOST'] as $k) {
  if (!preg_match("/define\(\s*['\"]".$k."['\"]\s*,\s*['\"](.*?)['\"]\s*\)/", $c, $m)) { fwrite(STDERR, "fehlt $k\n"); exit(1); }
  $w[$k] = stripcslashes($m[1]);
}
$cnf = getenv('HOME').'/.tmp/dump-'.getmypid().'.cnf';
touch($cnf); chmod($cnf, 0600);
file_put_contents($cnf, "[client]\nuser=\"".$w['DB_USER']."\"\npassword=\"".$w['DB_PASSWORD']."\"\nhost=\"".$w['DB_HOST']."\"\n");
passthru('mysqldump --defaults-extra-file='.escapeshellarg($cnf).' --single-transaction --default-character-set=utf8mb4 --no-tablespaces '.escapeshellarg($w['DB_NAME']), $rc);
unlink($cnf);
exit($rc);
"""


def sichern():
    ordner = os.path.join(UMZUG, f"wp-sicherung-{HEUTE}")
    os.makedirs(ordner, exist_ok=True)
    if not ssh(f"test -f {WEBORDNER}/wp-config.php && echo ja || true").strip():  # ohne WordPress Code 0 statt Abbruch (H2-10)
        sys.exit("Im Webordner liegt kein WordPress (wp-config.php fehlt) – nichts zu sichern. Schon umgezogen?")
    schritt("WordPress-Datenbank sichern")
    db = os.path.join(ordner, "datenbank-sccnld_db1.sql")
    with open(db, "wb") as f:
        ssh(f"cd {WEBORDNER} && php", daten=DBDUMP_PHP.encode(), ausgabe=f)
    ende = open(db, "rb").read()[-200:]
    if b"Dump completed" not in ende:
        sys.exit(f"Abbruch: Datenbank-Sicherung unvollständig ({db})")
    print(f"   {db} ({os.path.getsize(db) // 1024} KB)")
    schritt("WordPress-Dateien sichern (ca. 5 GB, dauert)")
    tar = os.path.join(ordner, "dateien-public_html.tar")
    with open(tar, "wb") as f:
        ssh(f"cd {WEBORDNER}/ && tar -cf - --exclude=./neu-test --exclude=./neu-probe .", ausgabe=f)
    with tarfile.open(tar) as t:
        namen = t.getnames()
    if not any(n.endswith("wp-config.php") for n in namen):
        sys.exit(f"Abbruch: Datei-Sicherung ohne wp-config.php ({tar})")
    print(f"   {tar} ({os.path.getsize(tar) // 1024 // 1024} MB, {len(namen)} Einträge)")
    return ordner


# ---------------------------------------------------------------- bauen
NICHT_AUSLIEFERN = ["werkzeuge", "wordpress-plugin", "UMZUG.md", "hochladen.ps1", "hochladen.bat", "ANLEITUNG.txt", ".gitignore",
                    "inhalte/LIESMICH.md"]


def bauen(ziel, domain, probe_pfad):
    if os.path.exists(ziel):
        shutil.rmtree(ziel)
    schritt("Seite zusammenstellen (wie GitHub)")
    dateien = subprocess.run(["git", "-C", REPO, "ls-files", "-z"], capture_output=True, check=True).stdout.decode().split("\0")
    n = 0
    for rel in dateien:
        if not rel or rel.startswith(".github/"):
            continue
        quelle = os.path.join(REPO, rel)
        if not os.path.isfile(quelle):
            continue  # im Arbeitsordner gelöscht
        os.makedirs(os.path.dirname(os.path.join(ziel, rel)), exist_ok=True)
        shutil.copy2(quelle, os.path.join(ziel, rel))
        n += 1
    print(f"   {n} Dateien")

    if os.path.isdir(BEITRAEGE_2025):
        schritt("Beiträge aus 2025 dazulegen")
        alt = open(os.path.join(BEITRAEGE_2025, "seiten", "news.html"), encoding="utf-8").read()
        for wurzel, _, namen in os.walk(BEITRAEGE_2025):
            for name in namen:
                rel = os.path.relpath(os.path.join(wurzel, name), BEITRAEGE_2025)
                if rel.replace("\\", "/") == "seiten/news.html":
                    continue
                os.makedirs(os.path.join(ziel, os.path.dirname(rel)), exist_ok=True)
                shutil.copy2(os.path.join(wurzel, name), os.path.join(ziel, rel))
        # Karten der 2025-Beiträge in die News-Grundlage (beitraege.py sortiert und baut Archiv)
        news_pfad = os.path.join(ziel, "seiten", "news.html")
        news = open(news_pfad, encoding="utf-8").read()
        da = set(re.findall(r'<a class="sp-karte" href="([^"]+)"', news))
        neu = [k for k in re.findall(r'<a class="sp-karte" href="[^"]+">.*?</a>', alt, re.S)
               if re.match(r'<a class="sp-karte" href="([^"]+)"', k).group(1) not in da]
        i = news.find('<div class="sp-karten"')
        j = news.find(">", i) + 1
        if i < 0:
            sys.exit("Abbruch: seiten/news.html ohne <div class=\"sp-karten\">")
        open(news_pfad, "w", encoding="utf-8", newline="").write(news[:j] + "".join(neu) + news[j:])
        print(f"   {len(neu)} Karten aus 2025 in die News")
    else:
        print(f"\n!! {BEITRAEGE_2025} fehlt – Beiträge aus 2025 bleiben draußen")

    schritt("Redaktionsbeiträge, neu/, Suchindex")
    py = sys.executable
    subprocess.run([py, os.path.join(ziel, "werkzeuge", "beitraege.py"), ziel], check=True)
    subprocess.run([py, os.path.join(ziel, "werkzeuge", "neu_seiten.py")], check=True)
    subprocess.run([py, os.path.join(ziel, "werkzeuge", "suche.py"), "index", ziel], check=True)
    shutil.rmtree(os.path.join(ziel, "werkzeuge", "__pycache__"), ignore_errors=True)

    schritt("Instagram-Karten von der Vorschau übernehmen")
    try:
        js = urllib.request.urlopen(urllib.request.Request(VORSCHAU + "instagram-daten.js", headers={"User-Agent": "SCH-Website"}), timeout=30).read()
        bilder = sorted(set(re.findall(rb'assets/instagram/[A-Za-z0-9._/-]+', js)))
        for b in bilder:
            p = os.path.join(ziel, b.decode())
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with urllib.request.urlopen(VORSCHAU + b.decode(), timeout=30) as r, open(p, "wb") as f:
                f.write(r.read())
        open(os.path.join(ziel, "instagram-daten.js"), "wb").write(js)
        print(f"   {len(bilder)} Bilder")
    except Exception as e:  # die Repo-Fassung (ohne Bilder) bleibt dann stehen; der nächste GitHub-Lauf ersetzt sie
        print(f"   nicht geklappt ({e}) – Repo-Fassung bleibt")

    schritt("Weiterleitungen alter WordPress-Adressen")
    ht = os.path.join(ziel, ".htaccess")
    subprocess.run([py, os.path.join(REPO, "werkzeuge", "weiterleitungen.py"), ht], check=True)
    if probe_pfad:
        # In /neu-probe/ zeigen die Ziele in den Probeordner; Google bekommt "noindex"
        t = open(ht, encoding="utf-8").read()
        t = re.sub(r"^(RewriteRule \S+) /", rf"\1 /{probe_pfad}/", t, flags=re.M)
        t += '\n<IfModule mod_headers.c>\nHeader set X-Robots-Tag "noindex, nofollow"\n</IfModule>\n'
        open(ht, "w", encoding="utf-8", newline="\n").write(t)

    schritt("Umzugs-Schalter")
    subprocess.run([py, os.path.join(REPO, "werkzeuge", "umzug_schalter.py"), ziel, domain], check=True)

    # Werkzeugdateien nicht auf den Webspace (Abnahme 16.11.2026 H3), wie im Pages-Bau (seite.yml)
    for rel in NICHT_AUSLIEFERN:
        p = os.path.join(ziel, rel)
        shutil.rmtree(p) if os.path.isdir(p) else os.path.exists(p) and os.remove(p)


# ---------------------------------------------------------------- hochladen
def packen(ordner):
    """tar-Strom mit festen Rechten (Dateien 644, Ordner 755), damit der Webserver alles lesen darf."""
    puffer = io.BytesIO()

    def rechte(info):
        info.mode = 0o755 if info.isdir() else 0o644
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        return info
    with tarfile.open(fileobj=puffer, mode="w", format=tarfile.PAX_FORMAT) as t:
        for name in sorted(os.listdir(ordner)):
            t.add(os.path.join(ordner, name), arcname=name, filter=rechte)
    return puffer.getvalue()


def hochladen(ordner):
    schritt("Hochladen in den Wartebereich ~/" + WARTEN)
    daten = packen(ordner)
    print(f"   {len(daten) // 1024 // 1024} MB")
    r = subprocess.run(ssh_befehl() + [f"rm -rf {WARTEN} && mkdir {WARTEN} && tar -xf - -C {WARTEN} --no-same-owner && find {WARTEN} -type f | wc -l"],
                       input=daten, capture_output=True)
    if r.returncode != 0:
        sys.exit("Abbruch beim Hochladen: " + r.stderr.decode("utf-8", "replace"))
    print(f"   {r.stdout.decode().strip()} Dateien auf dem Server")


def umschalten(ziel_im_web, alt_name):
    """Inhalt von ziel_im_web nach ~/alt_name verschieben, dann den Wartebereich hinein. Nichts wird gelöscht."""
    schritt(f"Umschalten: {ziel_im_web} (alter Inhalt -> ~/{alt_name})")
    ssh(
        "set -e; shopt -s dotglob nullglob; "
        f"test ! -e {alt_name} || {{ echo '~/{alt_name} gibt es schon'; exit 3; }}; "
        f"mkdir -p {ziel_im_web} {alt_name}; "
        f"for f in {ziel_im_web}/*; do mv \"$f\" {alt_name}/; done; "
        f"for f in {WARTEN}/*; do mv \"$f\" {ziel_im_web}/; done; "
        f"rmdir {WARTEN}; chmod 755 {ziel_im_web} 2>/dev/null || true"
    )


# ---------------------------------------------------------------- prüfen
def pruefen(basis):
    schritt("Prüfen: " + basis)
    fehler = 0
    for pfad, erwartet in (("", "<title>1. SC 1911"), ("seiten/news.html", "sp-karte"), ("seiten/impressum.html", "Impressum"),
                           ("seiten/datenschutz.html", "Hetzner"), ("seiten/suche.html", "su-feld"), ("suche-index.json", '"u":'),
                           ("newsletter.html", "")):
        try:
            with urllib.request.urlopen(urllib.request.Request(basis + pfad, headers={"User-Agent": "SCH-Website"}), timeout=30) as r:
                text = r.read().decode("utf-8", "replace")
                ok = erwartet in text
        except Exception as e:
            ok, text = False, str(e)
        fehler += not ok
        print(f"   {'ok ' if ok else 'FEHLER'}  {basis}{pfad}")
    # Eine alte WordPress-Adresse muss weiterleiten
    alt = basis + "2026/10/04/ende-im-achtelfinale-2/"
    req = urllib.request.Request(alt, headers={"User-Agent": "SCH-Website"}, method="HEAD")

    class Kein(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None
    try:
        urllib.request.build_opener(Kein).open(req, timeout=30)
        ziel, code = "", 200
    except urllib.error.HTTPError as e:
        ziel, code = e.headers.get("Location", ""), e.code
    ok = code == 301 and "spielbericht-erfurt.html" in ziel
    fehler += not ok
    print(f"   {'ok ' if ok else 'FEHLER'}  alte Adresse {alt} -> {code} {ziel}")
    return fehler


# ---------------------------------------------------------------- main
def main():
    art = sys.argv[1] if len(sys.argv) > 1 else ""
    ja = "--ja" in sys.argv
    if not os.path.isfile(SCHLUESSEL):
        sys.exit(f"SSH-Schlüssel fehlt: {SCHLUESSEL}")
    # Jedes Mal ein frischer Bauordner: unter Windows kann ein alter noch gesperrt sein (Explorer, Shell)
    for alt in [n for n in os.listdir(UMZUG) if n == "bau" or n.startswith("bau-")]:
        shutil.rmtree(os.path.join(UMZUG, alt), ignore_errors=True)
    bau = os.path.join(UMZUG, "bau-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    if art == "sichern":
        sichern()
    elif art == "probe":
        bauen(bau, DOMAIN + "neu-probe/", "neu-probe")
        hochladen(bau)
        ssh("rm -rf umzug-alt-probe")  # die vorige Probe
        umschalten(f"{WEBORDNER}/neu-probe", "umzug-alt-probe")
        f = pruefen(DOMAIN + "neu-probe/")
        print(f"\nProbe fertig: {DOMAIN}neu-probe/  ({'alles ok' if not f else f'{f} Fehler'})")
        sys.exit(1 if f else 0)
    elif art == "echt" and ja:
        ordner = sichern()
        bauen(bau, DOMAIN, "")
        hochladen(bau)
        umschalten(WEBORDNER, f"umzug-alt-wordpress-{HEUTE}")
        f = pruefen(DOMAIN)
        print(f"\nUmzug fertig ({'alles ok' if not f else f'{f} Fehler – prüfen, notfalls: python werkzeuge/umzug.py zurueck --ja'}).")
        print(f"WordPress liegt unverändert unter ~/umzug-alt-wordpress-{HEUTE}, Sicherung unter {ordner}")
        print("Weiter mit UMZUG.md (Newsletter-Worker, GitHub-Upload auf public_html, Search Console).")
    elif art == "zurueck" and ja:
        alt = ssh("ls -d umzug-alt-wordpress-* 2>/dev/null | tail -1").strip()
        if not alt:
            sys.exit("Kein beiseitegelegtes WordPress (~/umzug-alt-wordpress-*) gefunden.")
        ssh(f"set -e; shopt -s dotglob nullglob; test ! -e {WARTEN}; mkdir {WARTEN}; "
            f"for f in {WEBORDNER}/*; do mv \"$f\" {WARTEN}/; done; for f in {alt}/*; do mv \"$f\" {WEBORDNER}/; done; "
            f"rmdir {alt}; mv {WARTEN} umzug-neue-seite-zurueckgestellt-$(date +%Y%m%d-%H%M%S)")
        print(f"WordPress ist wieder da (aus ~/{alt}). Die neue Seite liegt unter ~/umzug-neue-seite-zurueckgestellt-*.")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
