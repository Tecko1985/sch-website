# Inhalte aus der Redaktion

Hier speichert die Redaktionsoberfläche (`/admin/`) die Beiträge, je Beitrag eine JSON-Datei.
Die Bilder liegen unter `assets/beitraege/`.

Beim Veröffentlichen (Workflow „Seite bauen“) macht `werkzeuge/beitraege.py` daraus die Beitragsseite,
die News-Liste und die Karten auf der Startseite, in beiden Designs. Die Dateien bitte nicht von Hand
umbenennen: Der Dateiname ist zugleich die Adresse des Beitrags (`seiten/beitrag-<name>.html`).
