# Umzug der Vereinsseite – Ablauf für den Umzugstag

Ziel: Die neue Seite ersetzt das WordPress auf www.sc1911-heiligenstadt.de.
Sie kommt auf den **Webspace bei Hetzner** (dedi1977.your-server.de), wo heute das WordPress liegt.
**Das Adressbuch (DNS) bei netmedia4you bleibt unverändert, die E-Mails bei Hetzner auch.**

## Schon vorbereitet

| Was | Wo |
|---|---|
| Weiterleitungen alter WordPress-Adressen (457 Stück, 301) | `.htaccess` ← `werkzeuge/weiterleitungen.py` |
| Impressum | `seiten/impressum.html` ← `werkzeuge/rechtliches.py` |
| Datenschutzerklärung für den Betrieb bei Hetzner | `seiten/datenschutz-neu.html` ← `werkzeuge/rechtliches.py` |
| Camp- und Popup-Fenster (vorher WordPress-Plugins) | `assets/fenster/`, eingebunden in `index.html` und `neu/index.html` |
| Platzhalter „Wir ziehen um“ | `umzug.html` ← `werkzeuge/umzug_seite.py` |
| Umzugs-Schalter (noindex raus, Domain, Impressum/Datenschutz verlinken, robots.txt, sitemap.xml) | `werkzeuge/umzug_schalter.py` |

**Beiträge aus 2025** (163 Stück mit Fotos) liegen bewusst **nicht** im Repo, weil das Repo öffentlich ist:
gesichert unter `E:\Vereine\SCH\_umzug\beitraege-2025\` (Michels Rechner). Sie kommen erst beim Umzug dazu.

## Am Umzugstag

1. **WordPress sichern**: alle Dateien und die Datenbank (`sccnld_db1`), per SSH oder über die konsoleH.
2. **Platzhalter zeigen** (optional, für die Zeit des Umbaus): `umzug.html` als `index.html` hochladen.
3. **Seite bauen** wie GitHub es tut: Repo-Dateien in einen Ordner kopieren, dann
   `python werkzeuge/beitraege.py <ordner>`, `python werkzeuge/suche.py index <ordner>` und `python <ordner>/werkzeuge/neu_seiten.py`.
   Nach Schritt 4 (Beiträge 2025) den Suchindex noch einmal erzeugen, damit sie gefunden werden.
4. **Beiträge aus 2025 dazulegen**: den Inhalt von `_umzug\beitraege-2025\` in den Ordner kopieren
   (inklusive `seiten/news.html`, die alle Karten enthält). Neu erzeugen geht auch:
   `python werkzeuge/alte_beitraege.py 2025`, solange das WordPress noch erreichbar ist.
5. **Weiterleitungen auffrischen**: `python werkzeuge/weiterleitungen.py` (holt neue WordPress-Beiträge mit).
6. **Schalter umlegen**: `python werkzeuge/umzug_schalter.py <ordner>`.
7. **Hochladen** per SFTP auf den Webspace (statt des WordPress), `.htaccess` nicht vergessen.
8. **Newsletter**: im Worker (`ToolsUebersicht/admin-worker.js`) `NL_SEITE_URL` auf
   `https://www.sc1911-heiligenstadt.de/newsletter.html` stellen und deployen.
9. **Prüfen**: Startseite, ein alter Beitragslink (z. B. `/2026/10/04/ende-im-achtelfinale-2/`),
   Impressum, Datenschutz, Newsletter-Anmeldung, Handy-Ansicht.
10. **Google Search Console**: Domain anmelden, `sitemap.xml` einreichen.

## Danach

- Automatisches Hochladen nach jedem Redaktionsbeitrag einrichten (GitHub Action per SFTP/SSH-Schlüssel).
- WordPress-Sicherung einige Wochen aufheben.
- Offene Punkte im Impressum klären: Telefonnummer (612202 oder 612206), „USt-IdNr.“ (sieht aus wie eine Steuernummer).
- Auftragsverarbeitungsvertrag mit Hetzner prüfen (in der konsoleH abschließbar).
