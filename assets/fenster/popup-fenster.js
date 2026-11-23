// Das Fenster auf der Vereins-Homepage.
//
// Wird dort EINMAL als <script src="…/popup.js" async> eingebaut und danach nie
// wieder angefasst. Welche Popups erscheinen, holt sich dieses Skript zur
// Laufzeit vom Worker — der Status in der App entscheidet, nicht die Homepage.
//
// ⚠️ Drei Dinge, die dieses Skript NICHT tun darf, weil es in einer FREMDEN
// Seite läuft (gleiche Linie wie E:\fussballcamp\popup.js):
//
//   1. Kein globales CSS. Alle Regeln hängen an #pu-popup-wurzel; ein
//      `* { box-sizing: border-box }` würde das Layout der ganzen Vereinsseite
//      umbauen. Das CSS steht deshalb hier inline.
//   2. Keine Cookies. Ob jemand ein Popup weggeklickt hat, merkt sich
//      localStorage — sonst bräuchte es eine Einwilligung im Cookie-Banner.
//   3. Nie einen Fehler nach außen lassen. Klemmt der Worker, passiert gar
//      nichts; eine kaputte Vereinsseite wäre der schlechtere Tausch.

(function () {
  "use strict";

  var GATEWAY = "https://sch-gateway.clubdach.de";
  var BILD_BASIS = GATEWAY + "/popup-bild/";
  var SPEICHER = "pu_popup_zu";
  var RUHE_TAGE = 7;
  // ⚠️ Zweite Fassung derselben Zahlen -- die erste steht als POPUP_GROESSEN
  // in config.js. Dieses Skript läuft eigenständig in der fremden Vereinsseite
  // und darf config.js nicht nachladen. Wer hier eine Zahl ändert, zieht
  // config.js mit.
  //
  // ⚠️ "px" und "vh" sind nur noch OBERGRENZEN für Fensterbreite und
  // Bildhöhe, keine feste Vorgabe mehr -- das Bild wird nie beschnitten
  // (volles Motiv sichtbar) und das Fenster passt seine Breite dem Bild an,
  // sodass weder Balken noch abgeschnittene Ränder entstehen (Rechenweg in
  // "zeigen()"). Trotzdem müssen beide Zahlen zusammen wachsen -- eine
  // größere Breite allein bringt bei einem breiten/queren Bild nichts, wenn
  // die Höhen-Obergrenze zuerst zuschlägt (Fund vom 20.09.2026, Michels
  // erstes Testbild war breiter als hoch; ein zweites Testbild war dann
  // hochkant-lastig und zeigte das Gegenteil: object-fit:cover schnitt die
  // Überschrift oben ab -- seitdem wird gar nicht mehr beschnitten).
  var GROESSEN = {
    klein: { px: 380, vh: 40 },
    mittel: { px: 520, vh: 56 },
    gross: { px: 720, vh: 70 }
  };

  // Zweimal eingebaut darf nicht zwei Fenster erzeugen.
  if (window.__puPopupLaeuft) return;
  window.__puPopupLaeuft = true;

  function bereit(fn) {
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", fn);
    else fn();
  }

  // Der Merkzettel hält fest, WELCHE Popups weggeklickt wurden. Ein neues
  // Popup ploppt dadurch wieder auf, auch wenn die Ruhefrist eines alten noch
  // läuft — sonst verpasst man die nächste Ankündigung, weil man die letzte
  // weggeklickt hat.
  function gemerkt() {
    try {
      var roh = window.localStorage.getItem(SPEICHER);
      if (!roh) return { bis: 0, ids: [] };
      var o = JSON.parse(roh);
      return { bis: Number(o.bis) || 0, ids: Array.isArray(o.ids) ? o.ids : [] };
    } catch (_) { return { bis: 0, ids: [] }; }
  }

  // ⚠️ Bugjagd 23.09.b T9-F14: DAZULEGEN, nicht ersetzen. Früher überschrieb
  // das Wegklicken von B die Liste — war A vorher weggeklickt, kam A innerhalb
  // der Ruhefrist beim nächsten Aufruf zurück. (Die Frist gilt danach für alle
  // gemerkten ab jetzt; eine Frist je Popup wäre mehr Aufwand als Nutzen.)
  function merken(ids) {
    try {
      var alt = gemerkt();
      var alle = (Date.now() < alt.bis ? alt.ids : []).slice();
      for (var i = 0; i < ids.length; i++) if (alle.indexOf(ids[i]) === -1) alle.push(ids[i]);
      if (alle.length > 50) alle = alle.slice(alle.length - 50);
      window.localStorage.setItem(SPEICHER, JSON.stringify({
        bis: Date.now() + RUHE_TAGE * 86400000,
        ids: alle
      }));
    } catch (_) { /* privater Modus ohne Speicher — dann eben jedes Mal wieder */ }
  }

  function stilEinbauen() {
    if (document.getElementById("pu-popup-stil")) return;
    var s = document.createElement("style");
    s.id = "pu-popup-stil";
    s.textContent = [
      '#pu-popup-wurzel{position:fixed;inset:0;z-index:99999;background:rgba(20,26,40,.6);',
      'display:flex;align-items:center;justify-content:center;padding:16px;',
      'font-family:"Segoe UI",system-ui,sans-serif;line-height:1.5;color:#1e2330}',
      '#pu-popup-wurzel *{box-sizing:border-box;margin:0;padding:0}',
      '#pu-popup-wurzel .pu-pop{background:#fff;border-radius:14px;max-width:520px;width:100%;',
      'max-height:calc(100vh - 32px);overflow-y:auto;box-shadow:0 8px 40px rgba(0,0,0,.3);position:relative}',
      '#pu-popup-wurzel .pu-pop-kopf{background:#1b2d4f;color:#fff;padding:18px 58px 18px 22px;border-radius:14px 14px 0 0}',
      '#pu-popup-wurzel .pu-pop-kopf h2{font-size:19px;margin:0;color:#fff;font-weight:600}',
      // Die Überschrift bekommt beim Öffnen den Fokus (für Bildschirmleser); ohne sichtbaren Rahmen
      '#pu-popup-wurzel .pu-pop-kopf h2:focus{outline:none}',
      '#pu-popup-wurzel .pu-pop-body{padding:18px 22px 22px}',
      '#pu-popup-wurzel .pu-pop-eintrag{border-bottom:1px solid #dde1e8;padding-bottom:16px;margin-bottom:16px}',
      '#pu-popup-wurzel .pu-pop-eintrag:last-of-type{border-bottom:none;margin-bottom:0;padding-bottom:0}',
      // Randlos über die volle Breite, wie beim Fußballcamp-Fenster: am Handy
      // bindet die Breite, ein seitliches Polster kostet dort unnötig Platz.
      '#pu-popup-wurzel .pu-pop-bildbox{margin:0 -22px 12px;text-align:center}',
      '#pu-popup-wurzel .pu-pop-eintrag:first-of-type .pu-pop-bildbox{margin-top:-18px}',
      // Kein festes max-height hier -- das würde die per JS berechnete Höhe
      // (die schon die richtige Grenze je Größe klein/mittel/groß nutzt)
      // unabhängig davon zusammendrücken und die Breite bliebe größer als sie
      // zur zusammengedrückten Höhe passt -- das Bild wirkt dann verzerrt
      // (gefunden 21.09.2026 bei "groß": JS rechnet mit 70vh, das CSS hatte
      // hart 56vh eingebaut).
      '#pu-popup-wurzel .pu-pop-bild{display:block;margin:0 auto;max-width:100%;width:auto;height:auto}',
      '#pu-popup-wurzel .pu-pop-titel{font-size:17px;font-weight:700;color:#1b2d4f;margin-bottom:6px}',
      '#pu-popup-wurzel .pu-pop-text{font-size:14px;margin-bottom:12px;white-space:pre-line}',
      '#pu-popup-wurzel .pu-pop-btn{display:inline-block;background:#267a43;color:#fff;border:none;',
      'border-radius:8px;padding:11px 20px;font-size:15px;font-weight:600;text-decoration:none;cursor:pointer}',
      '#pu-popup-wurzel .pu-pop-btn:hover{filter:brightness(1.08)}',
      // 44 x 44 px Trefferfläche fürs Kreuz (Erfahrung aus dem Camp-Fenster:
      // 31x30 px war am Handy kaum zu treffen).
      '#pu-popup-wurzel .pu-pop-zu{position:absolute;top:10px;right:10px;background:none;border:none;',
      'color:#fff;font-size:26px;line-height:1;cursor:pointer;padding:0;width:44px;height:44px;',
      'display:flex;align-items:center;justify-content:center}',
      '#pu-popup-wurzel .pu-pop-spaeter{display:inline-flex;align-items:center;min-height:44px;',
      'margin-top:6px;background:none;border:none;color:#6b7280;font-size:13px;',
      'text-decoration:underline;cursor:pointer;font-family:inherit;padding:0 2px}'
    ].join("");
    document.head.appendChild(s);
  }

  function esc(s) {
    return String(s === null || s === undefined ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  // Stehen mehrere Popups mit unterschiedlicher Größe gleichzeitig im selben
  // Fenster (sie teilen sich EIN Fenster, siehe unten), gewinnt die größte --
  // eine zu knappe Breite dürfte sonst ausgerechnet das größer gedachte
  // Popup beschneiden.
  //
  // ⚠️ Start bei 0, NICHT bei GROESSEN.mittel: sonst gewinnt "Mittel" als
  // stiller Bodensatz gegen ein einzelnes "Klein"-Popup (380 > 520 ist nie
  // wahr) -- genau der Fehler, den die Live-Probe am 20.09.2026 aufgedeckt
  // hat. Ohne jedes Popup (kommt praktisch nie vor) bleibt es bei Mittel.
  function groesseFuer(popups) {
    var beste = null, besteBreite = 0;
    popups.forEach(function (p) {
      var g = GROESSEN[p.groesse] || GROESSEN.mittel;
      if (g.px > besteBreite) { besteBreite = g.px; beste = g; }
    });
    return beste || GROESSEN.mittel;
  }

  function zeigen(popups) {
    stilEinbauen();

    // Solange das Fenster offen ist, darf die Seite dahinter nicht
    // scrollen -- sonst zeigt der Browser deren Scrollbalken durch das
    // Fenster hindurch. Nach dem Schließen exakt den vorherigen Wert
    // zurücksetzen (falls die Seite selbst schon einen eigenen Wert hatte).
    var vorherHtmlOverflow = document.documentElement.style.overflow;
    var vorherBodyOverflow = document.body.style.overflow;
    document.documentElement.style.overflow = "hidden";
    document.body.style.overflow = "hidden";

    // Fund 20.09.2026 (Abnahme): das Fenster poppt von SELBST auf, niemand
    // hat es angeklickt -- der Fokus muss trotzdem hinein, sonst merkt ein
    // Tastatur-/Vorleseprogramm-Nutzer gar nicht, dass gerade etwas
    // erschienen ist, und bedient munter die Seite dahinter weiter, obwohl
    // "aria-modal" das Gegenteil verspricht. Muster 1:1 aus
    // E:\ausbildungsplan\skizze.js (skFokusFalle/skFokusZurueck) übernommen
    // -- das einzige Fenster der Flotte, das das schon richtig macht.
    var vorherFokus = document.activeElement;

    var wurzel = document.createElement("div");
    wurzel.id = "pu-popup-wurzel";
    wurzel.setAttribute("role", "dialog");
    wurzel.setAttribute("aria-modal", "true");
    wurzel.setAttribute("aria-label", "Ankündigung");

    var ids = popups.map(function (p) { return p.id; });
    var mehrere = popups.length > 1;

    wurzel.innerHTML =
      '<div class="pu-pop">' +
        '<div class="pu-pop-kopf">' +
          '<h2 id="pu-pop-kopf-titel" tabindex="-1">' + (mehrere ? "Ankündigungen" : "Ankündigung") + '</h2>' +
          '<button type="button" class="pu-pop-zu" aria-label="Schließen">&times;</button>' +
        '</div>' +
        '<div class="pu-pop-body">' +
          popups.map(function (p) {
            var bild = p.id && p.bildId
              ? '<div class="pu-pop-bildbox"><img class="pu-pop-bild" alt="" src="' +
                  esc(BILD_BASIS + encodeURIComponent(p.id) + "/" + encodeURIComponent(p.bildId)) + '"></div>'
              : "";
            var knopf = (p.knopfText && p.knopfUrl)
              ? '<a class="pu-pop-btn" href="' + esc(p.knopfUrl) + '" target="_blank" rel="noopener">' + esc(p.knopfText) + '</a>'
              : "";
            return '<div class="pu-pop-eintrag">' +
              bild +
              '<div class="pu-pop-titel">' + esc(p.titel) + '</div>' +
              (p.text ? '<div class="pu-pop-text">' + esc(p.text) + '</div>' : "") +
              knopf +
            '</div>';
          }).join("") +
          '<button type="button" class="pu-pop-spaeter">Nicht mehr anzeigen</button>' +
        '</div>' +
      '</div>';

    var groesse = groesseFuer(popups);
    var pop = wurzel.querySelector(".pu-pop");
    pop.style.maxWidth = groesse.px + "px";

    function zu(dauerhaft) {
      if (dauerhaft) merken(ids);
      if (wurzel.parentNode) wurzel.parentNode.removeChild(wurzel);
      document.removeEventListener("keydown", beiTaste);
      document.removeEventListener("keydown", puFokusFalle);
      document.documentElement.style.overflow = vorherHtmlOverflow;
      document.body.style.overflow = vorherBodyOverflow;
      // Fokus zurück dorthin, wo er vor dem Aufpoppen war -- meist der
      // Seitenkörper (niemand hatte etwas fokussiert), aber falls jemand
      // gerade in einem Feld der Vereinsseite stand, bleibt er dort und
      // landet nicht kommentarlos ganz oben.
      if (vorherFokus && vorherFokus.isConnected && vorherFokus.offsetParent !== null) {
        try { vorherFokus.focus(); } catch (_) { /* Fokus ist Komfort, kein Muss */ }
      }
    }
    // ⚠️ Escape schließt nur EIN Fenster (Fund 21.09.2026, Abnahme Spur D):
    // stehen Ankündigungs- und Camp-Fenster (fussballcamp/popup.js, gleiche
    // Regel dort) gleichzeitig offen, schloss ein Escape sonst beide -- das
    // untere hatte der Tastatur-Nutzer nie gesehen. Geschlossen wird das
    // Fenster, in dem der Fokus steht; steht er in keinem, das oberste
    // (zuletzt eingehängte). Die Marke am Ereignis verhindert, dass nach dem
    // Schließen des einen (Fokus fällt dann auf die Seite) das andere im
    // selben Tastendruck als "jetzt oberstes" gleich mitgeht.
    function beiTaste(ev) {
      if (ev.key !== "Escape" || ev.scFensterZu) return;
      var aktivJetzt = document.activeElement;
      var imFenster = aktivJetzt && aktivJetzt.closest ? aktivJetzt.closest("[aria-modal='true']") : null;
      if (imFenster) {
        if (imFenster !== wurzel) return;
      } else {
        var alle = document.querySelectorAll("#pu-popup-wurzel, #fc-popup-wurzel");
        if (alle.length && alle[alle.length - 1] !== wurzel) return;
      }
      ev.scFensterZu = true;
      zu(false);
    }
    // Tab bleibt im Fenster: nach dem letzten Bedienelement kommt wieder das
    // erste (und umgekehrt mit Shift+Tab).
    //
    // ⚠️ Auf der Vereinsseite kann GLEICHZEITIG das Fußballcamp-Fenster (eigene
    // Falle `fcFokusFalle`) offen sein. Zogen beide Fallen den Fokus je in ihr
    // eigenes Fenster, blieb Tab auf dem ersten Knopf hängen. Deshalb gibt diese
    // Falle nach, sobald der Fokus in einem ANDEREN modalen Fenster steht: dann
    // bedient das andere Fenster Tab allein, und nach dessen Schließen greift
    // diese Falle wieder. Gegenstück: fussballcamp/popup.js (Commit e2221bd).
    function puFokusFalle(ev) {
      if (ev.key !== "Tab") return;
      var aktivJetzt = document.activeElement;
      var fremd = aktivJetzt && aktivJetzt.closest ? aktivJetzt.closest("[aria-modal='true']") : null;
      if (fremd && fremd !== wurzel) return;
      var ziele = Array.prototype.filter.call(
        wurzel.querySelectorAll("button, a[href], [tabindex]:not([tabindex='-1'])"),
        function (el) { return !el.disabled && el.offsetParent !== null; }
      );
      if (!ziele.length) { ev.preventDefault(); return; }
      var erstes = ziele[0], letztes = ziele[ziele.length - 1];
      var aktiv = document.activeElement;
      var drin = ziele.indexOf(aktiv) !== -1;
      if (ev.shiftKey && (!drin || aktiv === erstes)) { ev.preventDefault(); letztes.focus(); }
      else if (!ev.shiftKey && (!drin || aktiv === letztes)) { ev.preventDefault(); erstes.focus(); }
    }

    // ⚠️ "groesse.px"/"groesse.vh" sind nur noch OBERGRENZEN, keine feste
    // Vorgabe mehr. Das Bild wird NIE beschnitten (volles Motiv bleibt
    // sichtbar, Breite und Höhe im echten Seitenverhältnis skaliert) und das
    // Fenster passt seine eigene Breite dem breitesten Bild an -- so
    // entstehen weder Balken (Fenster breiter als das Bild) noch
    // abgeschnittene Ränder (Bild über die Höhengrenze hinaus gezwungen).
    // Fund vom 20.09.2026: object-fit:cover mit fester Höhe schnitt bei
    // einem hochkant-lastigen Bild oben die Überschrift ab -- das darf nicht
    // wieder passieren.
    var bilder = wurzel.querySelectorAll(".pu-pop-bild");
    var maxWpx = Math.min(groesse.px, window.innerWidth - 32);
    // 300px ist der geschätzte Platz für alles AUSSER dem Bild (Kopf ~65,
    // Innenabstand ~40, Titel ~32, Text ~33, Knopf ~45, "Nicht mehr
    // anzeigen" ~50, plus Rand-Polster des Overlays 32) -- eher zu viel als
    // zu wenig abgezogen, damit im Zweifel das Bild etwas kleiner wird statt
    // dass am Ende doch gescrollt werden muss.
    //
    // ⚠️ Fund 21.09.2026 (Abnahme, Handy QUER 812x375): dort ist die
    // 300px-Schätzung fast die ganze Schirmhöhe -- das Bild wurde auf 75 px
    // gedeckelt (Klein/Mittel/Groß wirkungslos), das Fenster schrumpfte auf
    // 280 px Breite, der Text brach auf vier Zeilen um und die Nachkorrektur
    // unten zog das Bild bis auf 0x0 zusammen. Quer gilt deshalb: Bildhöhe
    // relativ zur Schirmhöhe je Größe (mit Mindesthöhe), Fensterbreite nach
    // der gewählten Größe statt nach dem Bild, und das Fenster darf scrollen.
    // Hochkant und am Desktop bleibt alles wie bisher.
    var quer = window.innerWidth > window.innerHeight && window.innerHeight < 500;
    var maxHpx = quer
      ? Math.max(120, window.innerHeight * (groesse.vh / 100))
      : Math.min(window.innerHeight * (groesse.vh / 100), window.innerHeight - 300);
    var breiteste = 0;
    var offen = bilder.length;
    var bildDaten = [];
    var fertig = false;

    // ⚠️ Fund 20.09.2026 (Abnahme, Handy quer): die 300px-Schätzung oben
    // reicht nicht IMMER -- sobald der Text auf mehr als eine Zeile
    // umbricht (ganz gewöhnlicher Fall), blieb bei knapper Fensterhöhe
    // trotzdem ein Rest-Überlauf, und `.pu-pop` (overflow-y:auto) zeigte
    // wieder einen eigenen Scrollbalken. Deshalb NACH dem Layout (Bild UND
    // Fenster wirklich im Dokument, `pop.scrollHeight` also echt) noch
    // einmal messen und einen verbleibenden Rest vom BILD abziehen, nie von
    // der Breite -- eine schmalere Breite ließe den Text noch mehr umbrechen
    // und würde den Fehler verstärken statt beheben.
    function versucheFertigstellen() {
      if (fertig || offen > 0 || !wurzel.isConnected) return;
      fertig = true;
      if (breiteste > 0) pop.style.width = (quer ? maxWpx : Math.max(breiteste, 280)) + "px";
      // Quer nie am Bild sparen -- dort scrollt das Fenster lieber (siehe oben).
      if (quer) return;
      var ueberschuss = pop.scrollHeight - (window.innerHeight - 32);
      if (ueberschuss <= 0 || !bildDaten.length) return;
      var gesamtHoehe = bildDaten.reduce(function (s, d) { return s + d.img.offsetHeight; }, 0);
      if (gesamtHoehe <= 0) return;
      bildDaten.forEach(function (d) {
        var anteil = d.img.offsetHeight / gesamtHoehe;
        var neueHoehe = Math.max(0, Math.round(d.img.offsetHeight - ueberschuss * anteil));
        d.img.style.height = neueHoehe + "px";
        d.img.style.width = Math.round(neueHoehe * (d.nw / d.nh)) + "px";
      });
    }

    // ⚠️ Ein Bild, das nicht lädt, wird ENTFERNT statt als kaputtes Symbol
    // stehenzubleiben — dieselbe Überlegung wie im Fußballcamp-Fenster.
    Array.prototype.forEach.call(bilder, function (img) {
      function weg() {
        var box = img.parentNode;
        if (box && box.className === "pu-pop-bildbox" && box.parentNode) box.parentNode.removeChild(box);
        else if (box) box.removeChild(img);
        offen--;
        versucheFertigstellen();
      }
      function einpassen() {
        var nw = img.naturalWidth, nh = img.naturalHeight;
        if (!nw || !nh) { weg(); return; }
        var skala = Math.min(maxWpx / nw, maxHpx / nh);
        var breite = Math.round(nw * skala);
        img.style.display = "block";
        img.style.margin = "0 auto";
        img.style.width = breite + "px";
        img.style.height = Math.round(nh * skala) + "px";
        if (breite > breiteste) breiteste = breite;
        bildDaten.push({ img: img, nw: nw, nh: nh });
        offen--;
        versucheFertigstellen();
      }
      img.addEventListener("error", weg);
      if (img.complete) { if (img.naturalWidth) einpassen(); else weg(); }
      else img.addEventListener("load", einpassen);
    });

    wurzel.querySelector(".pu-pop-zu").addEventListener("click", function () { zu(false); });
    wurzel.querySelector(".pu-pop-spaeter").addEventListener("click", function () { zu(true); });
    wurzel.addEventListener("click", function (ev) { if (ev.target === wurzel) zu(false); });
    document.addEventListener("keydown", beiTaste);
    document.addEventListener("keydown", puFokusFalle);

    document.body.appendChild(wurzel);
    // Fokus erst NACH dem Einhängen setzen -- ein noch nicht im Dokument
    // hängendes Element lässt sich nicht fokussieren.
    var kopfTitel = wurzel.querySelector("#pu-pop-kopf-titel");
    if (kopfTitel) { try { kopfTitel.focus(); } catch (_) { /* Fokus ist Komfort, kein Muss */ } }
    // Deckt den Fall ab, dass alle Bilder schon vor dem Einhängen fertig
    // waren (aus dem Cache) -- dann lief `versucheFertigstellen()` oben
    // schon einmal ins Leere (`wurzel.isConnected` war noch false).
    versucheFertigstellen();
  }

  function los() {
    var merk = gemerkt();

    fetch(GATEWAY, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "popup-oeffentlich" })
    })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (antwort) {
        if (!antwort || !Array.isArray(antwort.popups) || !antwort.popups.length) return;

        var frist = Date.now() < merk.bis;
        var zeigbar = antwort.popups.filter(function (p) {
          return !(frist && merk.ids.indexOf(p.id) !== -1);
        });
        if (!zeigbar.length) return;

        // Kurz warten: sonst springt das Fenster auf, bevor die Seite selbst
        // steht, und wirkt wie ein Werbebanner.
        setTimeout(function () { try { zeigen(zeigbar); } catch (_) { /* still */ } }, 1200);
      })
      .catch(function () { /* Worker nicht erreichbar — dann eben kein Fenster */ });
  }

  bereit(function () { try { los(); } catch (_) { /* still */ } });
})();
