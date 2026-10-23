// Redaktion für die SCH-Testseite: Beiträge als JSON + Bilder per GitHub-API ins Repo schreiben.
// Der Pages-Bau (werkzeuge/beitraege.py) macht daraus Beitragsseite, Newsliste und Startseitenkarten.
(function () {
  'use strict';
  var REPO = 'Tecko1985/sch-website';
  var ZWEIG = 'main';
  var API = 'https://api.github.com/repos/' + REPO;
  var ORDNER = 'inhalte/beitraege/';
  var BILDER = 'assets/beitraege/';
  var SEITE = 'https://tecko1985.github.io/sch-website/';
  var SPEICHER = 'sch-redaktion-schluessel';

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  var schluessel = null;
  var beitraege = [];      // [{slug, daten, sha}]
  var aktuell = null;      // Beitrag im Editor
  var neueBilder = {};     // pfad -> base64 (noch nicht hochgeladen)

  // ---------------------------------------------------------------- GitHub
  function api(pfad, opt) {
    opt = opt || {};
    return fetch(pfad.indexOf('http') === 0 ? pfad : API + pfad, {
      method: opt.method || 'GET',
      headers: {
        'Authorization': 'Bearer ' + schluessel,
        'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28',
        'Content-Type': 'application/json'
      },
      body: opt.body ? JSON.stringify(opt.body) : undefined,
      cache: 'no-store'
    }).then(function (r) {
      if (r.status === 204) return null;
      return r.json().catch(function () { return {}; }).then(function (j) {
        if (!r.ok) { var e = new Error(j.message || ('Fehler ' + r.status)); e.status = r.status; throw e; }
        return j;
      });
    });
  }

  function textZuBase64(t) {
    var bytes = new TextEncoder().encode(t), s = '';
    for (var i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return btoa(s);
  }
  function base64ZuText(b) {
    var bin = atob(b.replace(/\n/g, '')), bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return new TextDecoder().decode(bytes);
  }

  // Mehrere Dateien in EINEM Commit schreiben bzw. löschen (inhalt === null).
  function commit(dateien, nachricht, versuch) {
    versuch = versuch || 1;
    var basis;
    return api('/git/ref/heads/' + ZWEIG).then(function (ref) {
      basis = ref.object.sha;
      return api('/git/commits/' + basis);
    }).then(function (c) {
      var baumBasis = c.tree.sha;
      return Promise.all(dateien.map(function (d) {
        if (d.inhalt === null) return Promise.resolve({ path: d.pfad, mode: '100644', type: 'blob', sha: null });
        return api('/git/blobs', { method: 'POST', body: { content: d.inhalt, encoding: 'base64' } })
          .then(function (b) { return { path: d.pfad, mode: '100644', type: 'blob', sha: b.sha }; });
      })).then(function (baum) {
        return api('/git/trees', { method: 'POST', body: { base_tree: baumBasis, tree: baum } });
      });
    }).then(function (baum) {
      return api('/git/commits', { method: 'POST', body: { message: nachricht, tree: baum.sha, parents: [basis] } });
    }).then(function (neu) {
      return api('/git/refs/heads/' + ZWEIG, { method: 'PATCH', body: { sha: neu.sha } });
    }).catch(function (e) {
      // Jemand anderes hat gerade gespeichert: einmal neu aufsetzen.
      if (versuch < 3 && (e.status === 422 || e.status === 409)) return commit(dateien, nachricht, versuch + 1);
      throw e;
    });
  }

  // ---------------------------------------------------------------- Anmelden
  function anmelden(s, merken) {
    schluessel = s;
    return api('').then(function (repo) {
      if (!repo.permissions || !repo.permissions.push) throw new Error('Der Schlüssel darf nicht in das Repository schreiben. Bei „Contents“ muss „Read and write“ stehen.');
      try {
        sessionStorage.setItem(SPEICHER, s);
        if (merken) localStorage.setItem(SPEICHER, s); else localStorage.removeItem(SPEICHER);
      } catch (e) {}
      $$('[data-nur-angemeldet]').forEach(function (el) { el.hidden = false; });
      holeVorlagen();
    });
  }
  function abmelden() {
    try { sessionStorage.removeItem(SPEICHER); localStorage.removeItem(SPEICHER); } catch (e) {}
    schluessel = null;
    location.hash = '';
    location.reload();
  }

  // ---------------------------------------------------------------- Ansichten
  function zeige(name) {
    $$('[data-ansicht]').forEach(function (el) { el.hidden = el.dataset.ansicht !== name; });
    window.scrollTo(0, 0);
  }

  function route() {
    if (!schluessel) { zeige('anmelden'); return; }
    var h = location.hash.replace('#', '');
    if (h === 'neu') { oeffneEditor(null); return; }
    if (h.indexOf('bearbeiten/') === 0) {
      var slug = h.slice(11);
      var b = beitraege.filter(function (x) { return x.slug === slug; })[0];
      if (b) { oeffneEditor(b); return; }
      ladeListe().then(function () {
        var b2 = beitraege.filter(function (x) { return x.slug === slug; })[0];
        if (b2) oeffneEditor(b2); else location.hash = 'liste';
      });
      return;
    }
    zeige('liste');
    ladeListe();
  }

  // ---------------------------------------------------------------- Liste
  function ladeListe() {
    var ul = $('[data-liste]');
    ul.innerHTML = '<li class="laedt">Lädt …</li>';
    return api('/contents/' + ORDNER.replace(/\/$/, '') + '?ref=' + ZWEIG).catch(function (e) {
      if (e.status === 404) return [];
      throw e;
    }).then(function (dateien) {
      dateien = (dateien || []).filter(function (d) { return /\.json$/.test(d.name); });
      return Promise.all(dateien.map(function (d) {
        return api('/contents/' + d.path + '?ref=' + ZWEIG).then(function (j) {
          return { slug: d.name.slice(0, -5), sha: j.sha, daten: JSON.parse(base64ZuText(j.content)) };
        });
      }));
    }).then(function (liste) {
      beitraege = liste.sort(function (a, b) { return (b.daten.datum + (b.daten.zeit || '')).localeCompare(a.daten.datum + (a.daten.zeit || '')); });
      zeichneListe();
    }).catch(function (e) {
      ul.innerHTML = '';
      var li = document.createElement('li');
      li.textContent = 'Liste konnte nicht geladen werden: ' + e.message;
      ul.appendChild(li);
    });
  }

  function zeichneListe() {
    var ul = $('[data-liste]');
    ul.innerHTML = '';
    $('[data-leer]').hidden = beitraege.length > 0;
    beitraege.forEach(function (b) {
      var d = b.daten;
      var li = document.createElement('li');
      var bild = d.bild ? '<img src="' + rohUrl(d.bild) + '" alt="" loading="lazy">' : '<span class="ohnebild"></span>';
      li.innerHTML = bild + '<div><b></b><small></small></div><div class="liste-aktionen">' +
        '<a class="klein-knopf" href="#bearbeiten/' + b.slug + '" style="display:inline-flex;align-items:center;text-decoration:none">Bearbeiten</a>' +
        (d.entwurf ? '' : '<a class="klein-knopf" target="_blank" rel="noopener" style="display:inline-flex;align-items:center;text-decoration:none" href="' + SEITE + 'seiten/beitrag-' + b.slug + '.html">Ansehen</a>') +
        '</div>';
      $('b', li).textContent = d.titel || 'Ohne Titel';
      $('small', li).textContent = datumDe(d.datum) + ' · ' + (d.rubrik || 'News');
      if (d.entwurf) { var m = document.createElement('span'); m.className = 'marke'; m.textContent = 'Entwurf'; $('b', li).appendChild(m); }
      ul.appendChild(li);
    });
  }

  function rohUrl(pfad) {
    if (neueBilder[pfad]) return 'data:image/webp;base64,' + neueBilder[pfad];
    return 'https://raw.githubusercontent.com/' + REPO + '/' + ZWEIG + '/' + pfad;
  }
  function datumDe(iso) { var t = (iso || '').split('-'); return t.length === 3 ? t[2] + '.' + t[1] + '.' + t[0] : iso; }

  // ---------------------------------------------------------------- Editor
  var form = $('[data-editor]');
  var textfeld = $('[data-text]');
  var titelbild = null;
  var galerie = [];

  function oeffneEditor(b) {
    aktuell = b;
    neueBilder = {};
    var d = b ? b.daten : {};
    $('[data-editortitel]').textContent = b ? 'Beitrag bearbeiten' : 'Neuer Beitrag';
    form.titel.value = d.titel || '';
    form.datum.value = d.datum || new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    form.rubrik.value = d.rubrik || 'News';
    form.teaser.value = d.teaser || '';
    form.entwurf.checked = !!d.entwurf;
    textfeld.innerHTML = d.text || '';
    titelbild = d.bild || null;
    galerie = (d.galerie || []).slice();
    zeichneBilder();
    unberuehrt = null;
    $('[data-vorlagewahl]').value = '';
    zeichneVorlagen();
    $('[data-loeschen]').hidden = !b;
    meldung('', '');
    aktualisiereKnopf();
    zeige('bearbeiten');
    setTimeout(function () { form.titel.focus(); }, 50);
  }

  function aktualisiereKnopf() {
    $('[data-speichern]').textContent = form.entwurf.checked ? 'Entwurf speichern' : (aktuell ? 'Änderungen veröffentlichen' : 'Veröffentlichen');
  }
  form.entwurf.addEventListener('change', aktualisiereKnopf);

  function zeichneBilder() {
    var tb = $('[data-titelbild]');
    tb.innerHTML = titelbild ? '<img alt="" src="' + rohUrl(titelbild) + '">' : '<p>Noch kein Bild</p>';
    $('[data-titelweg]').hidden = !titelbild;
    var g = $('[data-galerie]');
    g.innerHTML = '';
    galerie.forEach(function (pfad, i) {
      var f = document.createElement('figure');
      f.innerHTML = '<img alt="" src="' + rohUrl(pfad) + '"><button type="button" aria-label="Bild entfernen">×</button>';
      $('button', f).addEventListener('click', function () { galerie.splice(i, 1); zeichneBilder(); });
      g.appendChild(f);
    });
  }

  function meldung(text, art) {
    var m = $('[data-editormeldung]');
    m.textContent = text;
    m.className = 'meldung' + (art ? ' ' + art : '');
  }

  // Bilder im Browser verkleinern (max. 1600 px, WebP) – spart Speicher und Ladezeit.
  function bildVerkleinern(datei) {
    return new Promise(function (ok, fehler) {
      var url = URL.createObjectURL(datei);
      var img = new Image();
      img.onload = function () {
        var max = 1600, w = img.naturalWidth, h = img.naturalHeight, f = Math.min(1, max / Math.max(w, h));
        var c = document.createElement('canvas');
        c.width = Math.round(w * f); c.height = Math.round(h * f);
        c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
        URL.revokeObjectURL(url);
        var daten = c.toDataURL('image/webp', 0.82);
        if (daten.indexOf('data:image/webp') !== 0) daten = c.toDataURL('image/jpeg', 0.85); // ältere Safari
        ok({ base64: daten.split(',')[1], endung: daten.indexOf('image/webp') > 0 ? 'webp' : 'jpg' });
      };
      img.onerror = function () { URL.revokeObjectURL(url); fehler(new Error('Bild konnte nicht gelesen werden: ' + datei.name)); };
      img.src = url;
    });
  }

  function neuerBildpfad(endung) {
    return BILDER + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 7) + '.' + endung;
  }

  $('[data-titeldatei]').addEventListener('change', function (e) {
    var datei = e.target.files[0];
    if (!datei) return;
    meldung('Bild wird vorbereitet …', '');
    bildVerkleinern(datei).then(function (b) {
      var pfad = neuerBildpfad(b.endung);
      neueBilder[pfad] = b.base64;
      titelbild = pfad;
      zeichneBilder();
      meldung('', '');
    }).catch(function (err) { meldung(err.message, 'fehler'); });
    e.target.value = '';
  });
  $('[data-titelweg]').addEventListener('click', function () { titelbild = null; zeichneBilder(); });

  $('[data-galeriedatei]').addEventListener('change', function (e) {
    var dateien = Array.prototype.slice.call(e.target.files);
    if (!dateien.length) return;
    meldung('Bilder werden vorbereitet …', '');
    dateien.reduce(function (kette, datei) {
      return kette.then(function () {
        return bildVerkleinern(datei).then(function (b) {
          var pfad = neuerBildpfad(b.endung);
          neueBilder[pfad] = b.base64;
          galerie.push(pfad);
          zeichneBilder();
        });
      });
    }, Promise.resolve()).then(function () { meldung('', ''); }).catch(function (err) { meldung(err.message, 'fehler'); });
    e.target.value = '';
  });

  // Werkzeugleiste
  var linkDialog = $('[data-linkdialog]');
  var auswahl = null;
  $$('.werkzeuge button').forEach(function (b) {
    b.addEventListener('mousedown', function (e) { e.preventDefault(); }); // Auswahl im Text behalten
    b.addEventListener('click', function () {
      textfeld.focus();
      var befehl = b.dataset.befehl;
      if (befehl === 'link') {
        var sel = window.getSelection();
        auswahl = sel.rangeCount ? sel.getRangeAt(0).cloneRange() : null;
        linkDialog.querySelector('input').value = 'https://';
        linkDialog.returnValue = '';
        linkDialog.showModal();
        return;
      }
      if (befehl === 'formatBlock') {
        // Ein zweiter Klick auf Überschrift/Zitat macht wieder einen Absatz daraus
        var aktuellerBlock = document.queryCommandValue('formatBlock').toLowerCase();
        document.execCommand('formatBlock', false, aktuellerBlock === b.dataset.wert ? 'p' : b.dataset.wert);
        return;
      }
      if (befehl === 'platzhalter') { naechsterPlatzhalter(); return; }
      if (befehl === 'removeFormat') { document.execCommand('removeFormat'); document.execCommand('unlink'); document.execCommand('formatBlock', false, 'p'); return; }
      document.execCommand(befehl);
    });
  });
  linkDialog.addEventListener('close', function () {
    if (linkDialog.returnValue !== 'ok') return;
    var url = linkDialog.querySelector('input').value.trim();
    if (!/^(https?:|mailto:)/.test(url)) return;
    textfeld.focus();
    if (auswahl) { var s = window.getSelection(); s.removeAllRanges(); s.addRange(auswahl); }
    if (auswahl && auswahl.collapsed) document.execCommand('insertText', false, url);
    document.execCommand('createLink', false, url);
  });
  document.execCommand('defaultParagraphSeparator', false, 'p');

  // Einfügen nur als reiner Text (kein Word-/Webseiten-Ballast); Absätze bleiben erhalten
  textfeld.addEventListener('paste', function (e) {
    var t = (e.clipboardData || window.clipboardData).getData('text/plain');
    if (!t) return;
    e.preventDefault();
    var absaetze = t.replace(/\r/g, '').split(/\n{2,}/).map(function (a) {
      var esc = a.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/\n/g, '<br>');
      return '<p>' + esc + '</p>';
    }).join('');
    document.execCommand('insertHTML', false, absaetze.indexOf('</p><p>') < 0 ? absaetze.slice(3, -4) : absaetze);
  });

  // Lose Textstücke auf oberster Ebene in Absätze packen (z. B. die erste Zeile im leeren Feld)
  function normalisiereText() {
    var BLOCK = /^(P|H2|H3|UL|OL|BLOCKQUOTE|DIV)$/;
    var knoten = Array.prototype.slice.call(textfeld.childNodes), absatz = null;
    knoten.forEach(function (n) {
      var block = n.nodeType === 1 && BLOCK.test(n.nodeName);
      if (block) { absatz = null; return; }
      if (n.nodeType === 3 && !n.textContent.trim() && !absatz) { n.remove(); return; }
      if (n.nodeName === 'BR' && !absatz) { n.remove(); return; }
      if (!absatz) { absatz = document.createElement('p'); textfeld.insertBefore(absatz, n); }
      absatz.appendChild(n);
    });
  }

  // ---------------------------------------------------------------- Vorlagen
  // Gerüste für wiederkehrende Beiträge. Sie liegen gemeinsam für alle in inhalte/vorlagen.json
  // (der Seitenbau liest nur inhalte/beitraege/). Solange die Datei fehlt, gelten die Grundvorlagen.
  var VORLAGEN = 'inhalte/vorlagen.json';
  var GRUND = [
    { id: 'grund-spielbericht', name: 'Spielbericht', rubrik: 'Spielbericht', standard: true,
      titel: '[Sieg/Remis/Niederlage] gegen [Gegner]',
      teaser: '[Ergebnis in einem Satz: Wer hat wie gespielt?]',
      text: '<p><b>[Liga], [Spieltag]. Spieltag: SC 1911 Heiligenstadt – [Gegner] [Tore]:[Tore] ([Halbzeit])</b></p>' +
        '<h2>Spielverlauf</h2><p>[Wie lief die erste Halbzeit?]</p><p>[Wie lief die zweite Halbzeit?]</p>' +
        '<h2>Stimmen zum Spiel</h2><blockquote>[Zitat Trainer oder Spieler]</blockquote>' +
        '<h2>Aufstellung und Tore</h2><p><b>SCH:</b> [Aufstellung]</p><p><b>Tore:</b> [Minute, Torschütze]</p>' +
        '<h2>Wie geht es weiter?</h2><p>[Nächstes Spiel: Tag, Datum, Uhrzeit, Gegner, Ort]</p>' },
    { id: 'grund-vorbericht', name: 'Vorbericht', rubrik: 'Vorbericht', standard: true,
      titel: 'Vorschau: SCH gegen [Gegner]',
      teaser: '[Worum geht es am Wochenende?]',
      text: '<h2>Die Ausgangslage</h2><p>[Tabellenplatz, letzte Ergebnisse, Bilanz gegen den Gegner]</p>' +
        '<h2>Personal</h2><p>[Wer fehlt, wer kommt zurück?]</p>' +
        '<h2>Anpfiff</h2><ul><li><b>Wann:</b> [Tag, Datum, Uhrzeit]</li><li><b>Wo:</b> [Sportplatz, Ort]</li><li><b>Eintritt:</b> [Preis]</li></ul>' +
        '<p>[Aufruf an die Fans]</p>' },
    { id: 'grund-nachwuchs', name: 'Nachwuchs', rubrik: 'Nachwuchs', standard: true,
      titel: '[Mannschaft, z. B. D-Jugend]: [Kurzmeldung]',
      teaser: '[Was ist passiert?]',
      text: '<p>[Was ist passiert? Spiel, Turnier, Ausflug …]</p><p>[Besondere Momente, Ergebnisse]</p>' +
        '<h2>Danke</h2><p>[Dank an Trainer, Eltern, Helfer, Sponsoren]</p>' },
    { id: 'grund-verein', name: 'Vereinsnachricht', rubrik: 'Verein', standard: true,
      titel: '[Thema]',
      teaser: '[Worum geht es in einem Satz?]',
      text: '<p>[Worum geht es?]</p><ul><li><b>Wann:</b> [Datum, Uhrzeit]</li><li><b>Wo:</b> [Ort]</li></ul>' +
        '<p><b>Fragen?</b> [Ansprechpartner, Kontakt]</p>' },
    { id: 'grund-news', name: 'Kurzmeldung', rubrik: 'News', standard: false,
      titel: '[Überschrift]',
      teaser: '',
      text: '<p>[Die Nachricht in zwei, drei Sätzen.]</p><p>[Mehr Infos oder Link]</p>' }
  ];
  var vorlagen = [];
  var vorlagenOk = false;   // false = Datei nicht lesbar; dann wird nichts gespeichert, damit nichts überschrieben wird
  var unberuehrt = null;    // Stand direkt nach dem Einsetzen einer Vorlage
  var vorlageWahl = $('[data-vorlagewahl]');
  var vorlageDialog = $('[data-vorlagedialog]');

  function kopie(x) { return JSON.parse(JSON.stringify(x)); }
  function vorlageNach(id) { return vorlagen.filter(function (v) { return v.id === id; })[0]; }

  function ladeVorlagen() {
    return api('/contents/' + VORLAGEN + '?ref=' + ZWEIG).then(function (j) {
      var liste = JSON.parse(base64ZuText(j.content));
      return Array.isArray(liste) ? liste : [];
    }).catch(function (e) {
      if (e.status === 404) return kopie(GRUND);
      throw e;
    });
  }
  function holeVorlagen() {
    return ladeVorlagen().then(function (l) { vorlagen = l; vorlagenOk = true; })
      .catch(function () { vorlagen = kopie(GRUND); vorlagenOk = false; })
      .then(zeichneVorlagen);
  }
  // Frisch laden, ändern, schreiben – so gehen Vorlagen anderer nicht verloren.
  // [skip ci]: Vorlagen ändern nichts an der Seite, also kein Neubau.
  function speichereVorlagen(aendern, nachricht) {
    return ladeVorlagen().then(function (liste) {
      liste = aendern(liste);
      return commit([{ pfad: VORLAGEN, inhalt: textZuBase64(JSON.stringify(liste, null, 2) + '\n') }], nachricht + ' (Redaktion) [skip ci]')
        .then(function () { vorlagen = liste; vorlagenOk = true; zeichneVorlagen(); });
    });
  }

  function zeichneVorlagen() {
    var alt = vorlageWahl.value, rubrik = form.rubrik.value;
    var sortiert = vorlagen.slice().sort(function (a, b) { return a.name.localeCompare(b.name, 'de'); });
    vorlageWahl.innerHTML = '';
    vorlageWahl.appendChild(new Option(vorlagen.length ? '– Vorlage einsetzen –' : '– noch keine Vorlagen –', ''));
    [[rubrik, true], ['Andere Rubriken', false]].forEach(function (g) {
      var teil = sortiert.filter(function (v) { return (v.rubrik === rubrik) === g[1]; });
      if (!teil.length) return;
      var og = document.createElement('optgroup');
      og.label = g[0];
      teil.forEach(function (v) {
        og.appendChild(new Option(v.name + (g[1] ? (v.standard ? ' (Standard)' : '') : ' · ' + v.rubrik), v.id));
      });
      vorlageWahl.appendChild(og);
    });
    vorlageWahl.value = vorlageNach(alt) ? alt : '';
    $('[data-vorlageweg]').hidden = !vorlageWahl.value;
  }

  function stand() { return form.titel.value + '\u0001' + form.teaser.value + '\u0001' + textfeld.innerHTML; }
  function istUnberuehrt() {
    return (!form.titel.value.trim() && !form.teaser.value.trim() && !textfeld.textContent.trim()) || stand() === unberuehrt;
  }

  function setzeVorlage(v) {
    form.rubrik.value = v.rubrik;
    form.titel.value = v.titel || '';
    form.teaser.value = v.teaser || '';
    textfeld.innerHTML = v.text || '';
    unberuehrt = stand();
    vorlageWahl.value = v.id;
    zeichneVorlagen();
    meldung('Vorlage „' + v.name + '“ eingesetzt. Jetzt die [Platzhalter] ausfüllen.', 'ok');
  }

  vorlageWahl.addEventListener('change', function () {
    var v = vorlageNach(vorlageWahl.value);
    $('[data-vorlageweg]').hidden = !v;
    if (!v) return;
    if (!istUnberuehrt() && !window.confirm('Titel, Anreißer und Text werden durch die Vorlage „' + v.name + '“ ersetzt. Weiter?')) {
      vorlageWahl.value = ''; $('[data-vorlageweg]').hidden = true; return;
    }
    setzeVorlage(v);
  });

  // Neuer, noch leerer Beitrag: Standardvorlage der Rubrik einsetzen
  form.rubrik.addEventListener('change', function () {
    var rubrik = form.rubrik.value;
    var v = vorlagen.filter(function (x) { return x.rubrik === rubrik && x.standard; })[0];
    if (v && !aktuell && istUnberuehrt()) { setzeVorlage(v); return; }
    zeichneVorlagen();
  });

  $('[data-vorlagespeichern]').addEventListener('click', function () {
    if (!vorlagenOk) { meldung('Die Vorlagen konnten nicht geladen werden. Bitte die Seite neu laden.', 'fehler'); return; }
    normalisiereText();
    if (!form.titel.value.trim() && !textfeld.textContent.trim()) { meldung('Erst Titel oder Text schreiben, dann als Vorlage speichern.', 'fehler'); return; }
    var gewaehlt = vorlageNach(vorlageWahl.value);
    var passt = gewaehlt && gewaehlt.rubrik === form.rubrik.value;
    vorlageDialog.querySelector('[name=name]').value = passt ? gewaehlt.name : '';
    vorlageDialog.querySelector('[name=standard]').checked = passt ? !!gewaehlt.standard :
      !vorlagen.some(function (v) { return v.rubrik === form.rubrik.value && v.standard; });
    $('[data-vorlagerubrik]').textContent = '„' + form.rubrik.value + '“';
    vorlageDialog.returnValue = '';   // sonst gilt nach Esc noch das „ok“ vom letzten Mal
    vorlageDialog.showModal();
  });

  vorlageDialog.addEventListener('close', function () {
    if (vorlageDialog.returnValue !== 'ok') return;
    var name = vorlageDialog.querySelector('[name=name]').value.trim();
    if (!name) return;
    var neu = {
      id: '', name: name, rubrik: form.rubrik.value,
      titel: form.titel.value.trim(), teaser: form.teaser.value.trim(), text: textfeld.innerHTML.trim(),
      standard: vorlageDialog.querySelector('[name=standard]').checked
    };
    var gleich = function (v) { return v.rubrik === neu.rubrik && v.name.toLowerCase() === name.toLowerCase(); };
    var vorhanden = vorlagen.filter(gleich)[0];
    if (vorhanden && vorhanden.id !== vorlageWahl.value &&
        !window.confirm('Es gibt schon eine Vorlage „' + vorhanden.name + '“ in der Rubrik ' + neu.rubrik + '. Überschreiben?')) return;
    meldung('Vorlage wird gespeichert …', '');
    speichereVorlagen(function (liste) {
      var alt = liste.filter(gleich)[0];
      neu.id = alt ? alt.id : 'v-' + Date.now().toString(36);
      if (neu.standard) liste.forEach(function (v) { if (v.rubrik === neu.rubrik) v.standard = false; });
      return liste.filter(function (v) { return v.id !== neu.id; }).concat([neu]);
    }, (vorhanden ? 'Vorlage geändert: ' : 'Neue Vorlage: ') + name).then(function () {
      vorlageWahl.value = neu.id;
      unberuehrt = stand();
      zeichneVorlagen();
      meldung('Vorlage „' + name + '“ gespeichert. Sie steht jetzt allen in der Redaktion zur Verfügung.', 'ok');
    }).catch(function (err) { meldung('Vorlage nicht gespeichert: ' + err.message, 'fehler'); });
  });

  $('[data-vorlageweg]').addEventListener('click', function () {
    var v = vorlageNach(vorlageWahl.value);
    if (!v) return;
    if (!vorlagenOk) { meldung('Die Vorlagen konnten nicht geladen werden. Bitte die Seite neu laden.', 'fehler'); return; }
    if (!window.confirm('Vorlage „' + v.name + '“ für alle in der Redaktion löschen? Der Beitrag im Editor bleibt, wie er ist.')) return;
    meldung('Vorlage wird gelöscht …', '');
    speichereVorlagen(function (liste) {
      return liste.filter(function (x) { return x.id !== v.id; });
    }, 'Vorlage gelöscht: ' + v.name).then(function () {
      meldung('Vorlage „' + v.name + '“ gelöscht.', 'ok');
    }).catch(function (err) { meldung('Löschen fehlgeschlagen: ' + err.message, 'fehler'); });
  });

  // [Platzhalter] aus Vorlagen finden und der Reihe nach markieren
  var PLATZHALTER = /\[[^\]\n]{1,80}\]/g;
  function offenePlatzhalter() {
    var gefunden = (form.titel.value + '\n' + form.teaser.value + '\n' + textfeld.textContent).match(PLATZHALTER) || [];
    return gefunden.filter(function (p, i) { return gefunden.indexOf(p) === i; });
  }
  function naechsterPlatzhalter() {
    var treffer = [], n, m;
    var gang = document.createTreeWalker(textfeld, NodeFilter.SHOW_TEXT);
    while ((n = gang.nextNode())) {
      PLATZHALTER.lastIndex = 0;
      while ((m = PLATZHALTER.exec(n.data))) treffer.push({ n: n, a: m.index, b: m.index + m[0].length });
    }
    if (!treffer.length) {
      var rest = offenePlatzhalter();
      meldung(rest.length ? 'Im Text ist alles ausgefüllt. Noch offen in Titel oder Anreißer: ' + rest.join(', ') : 'Keine Platzhalter mehr offen.', rest.length ? 'fehler' : 'ok');
      return;
    }
    var sel = window.getSelection(), ziel = treffer[0];
    if (sel.rangeCount && textfeld.contains(sel.getRangeAt(0).endContainer)) {
      var hier = sel.getRangeAt(0).cloneRange();
      hier.collapse(false);
      for (var i = 0; i < treffer.length; i++) {
        if (hier.comparePoint(treffer[i].n, treffer[i].a) >= 0) { ziel = treffer[i]; break; }
      }
    }
    var r = document.createRange();
    r.setStart(ziel.n, ziel.a); r.setEnd(ziel.n, ziel.b);
    sel.removeAllRanges(); sel.addRange(r);
    if (ziel.n.parentNode.scrollIntoView) ziel.n.parentNode.scrollIntoView({ block: 'center' });
  }

  function slugAus(titel, datum) {
    var s = (titel || 'beitrag').toLowerCase()
      .replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue').replace(/ß/g, 'ss')
      .normalize('NFKD').replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60).replace(/-+$/, '');
    var basis = datum + '-' + (s || 'beitrag'), slug = basis, n = 2;
    while (beitraege.some(function (b) { return b.slug === slug; })) slug = basis + '-' + n++;
    return slug;
  }

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    var titel = form.titel.value.trim();
    if (!titel) { meldung('Bitte einen Titel eintragen.', 'fehler'); form.titel.focus(); return; }
    if (!form.datum.value) { meldung('Bitte ein Datum wählen.', 'fehler'); form.datum.focus(); return; }
    normalisiereText();
    var text = textfeld.innerHTML.trim();
    if (!textfeld.textContent.trim() && !form.entwurf.checked) { meldung('Der Text ist noch leer.', 'fehler'); textfeld.focus(); return; }
    var offen = offenePlatzhalter();
    if (offen.length && !form.entwurf.checked &&
        !window.confirm('Im Beitrag stehen noch Platzhalter aus der Vorlage: ' + offen.slice(0, 5).join(', ') + (offen.length > 5 ? ' …' : '') + '\n\nTrotzdem veröffentlichen?')) return;

    var slug = aktuell ? aktuell.slug : slugAus(titel, form.datum.value);
    var vorher = aktuell ? aktuell.daten : {};
    var daten = {
      titel: titel,
      datum: form.datum.value,
      zeit: vorher.zeit || new Date().toTimeString().slice(0, 5),
      rubrik: form.rubrik.value,
      teaser: form.teaser.value.trim(),
      bild: titelbild || '',
      text: text,
      galerie: galerie.slice(),
      entwurf: form.entwurf.checked
    };
    var dateien = [{ pfad: ORDNER + slug + '.json', inhalt: textZuBase64(JSON.stringify(daten, null, 2) + '\n') }];
    Object.keys(neueBilder).forEach(function (pfad) {
      if (pfad === titelbild || galerie.indexOf(pfad) >= 0) dateien.push({ pfad: pfad, inhalt: neueBilder[pfad] });
    });
    // Nicht mehr benutzte Bilder dieses Beitrags entfernen
    [vorher.bild].concat(vorher.galerie || []).forEach(function (p) {
      if (p && p.indexOf(BILDER) === 0 && p !== titelbild && galerie.indexOf(p) < 0) dateien.push({ pfad: p, inhalt: null });
    });

    var knopf = $('[data-speichern]');
    knopf.disabled = true;
    meldung('Wird gespeichert …', '');
    var art = daten.entwurf ? 'Entwurf' : (aktuell ? 'Beitrag geändert' : 'Neuer Beitrag');
    commit(dateien, art + ': ' + titel + ' (Redaktion)').then(function () {
      neueBilder = {};
      var eintrag = { slug: slug, daten: daten };
      beitraege = beitraege.filter(function (b) { return b.slug !== slug; }).concat([eintrag]);
      aktuell = eintrag;
      $('[data-loeschen]').hidden = false;
      meldung(daten.entwurf ? 'Entwurf gespeichert.' : 'Gespeichert. Der Beitrag ist in etwa 2 Minuten auf der Seite.', 'ok');
      if (!daten.entwurf) zeigeLiveHinweis(slug, titel);
      history.replaceState(null, '', '#bearbeiten/' + slug);
    }).catch(function (err) {
      meldung('Speichern fehlgeschlagen: ' + err.message, 'fehler');
    }).then(function () { knopf.disabled = false; aktualisiereKnopf(); });
  });

  $('[data-loeschen]').addEventListener('click', function () {
    if (!aktuell) return;
    if (!window.confirm('„' + (aktuell.daten.titel || 'Beitrag') + '“ wirklich löschen? Das lässt sich hier nicht rückgängig machen.')) return;
    var d = aktuell.daten;
    var dateien = [{ pfad: ORDNER + aktuell.slug + '.json', inhalt: null }];
    [d.bild].concat(d.galerie || []).forEach(function (p) { if (p && p.indexOf(BILDER) === 0) dateien.push({ pfad: p, inhalt: null }); });
    meldung('Wird gelöscht …', '');
    commit(dateien, 'Beitrag gelöscht: ' + (d.titel || aktuell.slug) + ' (Redaktion)').then(function () {
      var slug = aktuell.slug;
      beitraege = beitraege.filter(function (b) { return b.slug !== slug; });
      aktuell = null;
      location.hash = 'liste';
    }).catch(function (err) { meldung('Löschen fehlgeschlagen: ' + err.message, 'fehler'); });
  });

  function zeigeLiveHinweis(slug, titel) {
    var h = $('[data-livehinweis]');
    h.hidden = false;
    h.innerHTML = '';
    h.appendChild(document.createTextNode('„' + titel + '“ wird gerade veröffentlicht. In etwa 2 Minuten: '));
    var a = document.createElement('a');
    a.href = SEITE + 'seiten/beitrag-' + slug + '.html';
    a.target = '_blank'; a.rel = 'noopener';
    a.textContent = 'Beitrag ansehen';
    h.appendChild(a);
  }

  // Vor dem Verlassen mit ungespeicherten Bildern warnen
  window.addEventListener('beforeunload', function (e) {
    if (Object.keys(neueBilder).length) { e.preventDefault(); e.returnValue = ''; }
  });

  // ---------------------------------------------------------------- Start
  $('[data-anmeldeform]').addEventListener('submit', function (e) {
    e.preventDefault();
    var f = e.target, m = $('[data-anmeldemeldung]');
    m.className = 'meldung'; m.textContent = 'Wird geprüft …';
    anmelden(f.schluessel.value.trim(), f.merken.checked).then(function () {
      f.reset(); m.textContent = '';
      route();
    }).catch(function (err) {
      schluessel = null;
      m.className = 'meldung fehler';
      m.textContent = err.status === 401 ? 'Der Schlüssel ist ungültig oder abgelaufen.' : err.status === 404 ? 'Mit diesem Schlüssel ist das Repository nicht erreichbar. Ist „sch-website“ ausgewählt?' : err.message;
    });
  });
  $('[data-abmelden]').addEventListener('click', abmelden);
  window.addEventListener('hashchange', route);

  var gemerkt = null;
  try { gemerkt = sessionStorage.getItem(SPEICHER) || localStorage.getItem(SPEICHER); } catch (e) {}
  if (gemerkt) {
    anmelden(gemerkt, !!(function () { try { return localStorage.getItem(SPEICHER); } catch (e) { return null; } })())
      .then(route)
      .catch(function () { schluessel = null; try { sessionStorage.removeItem(SPEICHER); localStorage.removeItem(SPEICHER); } catch (e) {} route(); });
  } else {
    route();
  }
})();
