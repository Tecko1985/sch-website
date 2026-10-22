# Neue Startseite in WordPress einbauen

Das Plugin **SC 1911 Startseite** zeigt die neue Startseite auf www.sc1911-heiligenstadt.de.

- **News** kommen live aus WordPress: die 3 neuesten oben, die nächsten 8 darunter.
- **Spiele und Ergebnisse** holt der Webserver alle 30 Minuten selbst von FuPa.
  Besucher laden dabei nichts bei FuPa.
- **Spielberichte** werden von selbst verlinkt. Es zählt der erste Beitrag nach dem
  Spiel, der kein „MATCHDAY“ und keine Wochenendübersicht ist. Das gilt für die
  1. und die 2. Mannschaft.
- Alle anderen Seiten (News, Verein, Nachwuchs …) bleiben wie sie sind.

## Einbauen – Schritt für Schritt

1. **Vorher eine Sicherung** der WordPress-Seite machen, zum Beispiel über die Sicherung
   beim Webhoster.
2. In WordPress: **Plugins → Installieren → Plugin hochladen** und dann
   `sc1911-startseite.zip` auswählen. Danach **Aktivieren**.
   Besucher sehen jetzt **noch nichts Neues**.
3. **Vorschau ansehen:** angemeldet `https://www.sc1911-heiligenstadt.de/?sch-neu=1` öffnen.
   Links unten steht „Vorschau“. Alles am Computer und am Handy durchklicken.
4. **Datenschutz ergänzen:** Seite „Datenschutz“ bearbeiten, einen Block
   „Individuelles HTML“ einfügen und den Inhalt von `datenschutz-newsletter.txt`
   hineinkopieren. Das ist Pflicht, weil die Startseite ein Newsletter-Formular hat.
5. **Einschalten:** Einstellungen → **SC Startseite** → Haken bei
   „Neue Startseite für alle Besucher einschalten“ → Speichern.
   Wenn die Seite ein Cache-Plugin nutzt, danach dort den Cache leeren.

## Zurück zur alten Startseite

Einstellungen → SC Startseite → Haken raus, oder das Plugin deaktivieren.
Die alte Startseite ist dann sofort wieder da. Nichts geht verloren.

## Wenn das Design geändert wird

Das Design kommt aus `index.html` und den CSS-/JS-Dateien in diesem Repo. Nach einer Änderung:

```
python wordpress-plugin/baue-plugin.py
```

Danach das neue `sc1911-startseite.zip` in WordPress hochladen. WordPress fragt dann,
ob es die alte Fassung ersetzen soll: mit **Ja** bestätigen.

## Gut zu wissen

- Das Theme (Enfold) wird auf der Startseite nicht geladen. Die Seite bringt ihr
  eigenes Design mit. Andere Plugins, zum Beispiel der Cookie-Banner, laufen weiter.
- Die Instagram-Beiträge (die automatischen Karten) gibt es nur auf der GitHub-Seite.
  Im Plugin stehen die drei festen Karten: Facebook, Instagram und Instagram Nachwuchs.
- Bestätigen und Abmelden beim Newsletter läuft weiter über
  `tecko1985.github.io/sch-website/newsletter.html`.
- Geprüft mit WordPress 6.x und PHP 7.4 in einem Test-WordPress, aber nicht mit Enfold.
  Deshalb erst die Vorschau ansehen (Schritt 3).
