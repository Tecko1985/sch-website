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
  // dateien darf auch eine Funktion (basisCommitSha) -> Promise<dateien> sein: Sie prüft gegen genau
  // den Stand, auf dem der Commit aufbaut, und läuft bei jedem Neuversuch wieder.
  // Ergebnis: { pfad: blobSha } der geschriebenen Dateien.
  function commit(dateien, nachricht, versuch) {
    versuch = versuch || 1;
    var basis, shas = {};
    return api('/git/ref/heads/' + ZWEIG).then(function (ref) {
      basis = ref.object.sha;
      return Promise.all([api('/git/commits/' + basis), typeof dateien === 'function' ? dateien(basis) : dateien]);
    }).then(function (r) {
      var baumBasis = r[0].tree.sha;
      return Promise.all(r[1].map(function (d) {
        if (d.inhalt === null) return Promise.resolve({ path: d.pfad, mode: '100644', type: 'blob', sha: null });
        return api('/git/blobs', { method: 'POST', body: { content: d.inhalt, encoding: 'base64' } })
          .then(function (b) { shas[d.pfad] = b.sha; return { path: d.pfad, mode: '100644', type: 'blob', sha: b.sha }; });
      })).then(function (baum) {
        return api('/git/trees', { method: 'POST', body: { base_tree: baumBasis, tree: baum } });
      });
    }).then(function (baum) {
      return api('/git/commits', { method: 'POST', body: { message: nachricht, tree: baum.sha, parents: [basis] } });
    }).then(function (neu) {
      return api('/git/refs/heads/' + ZWEIG, { method: 'PATCH', body: { sha: neu.sha } });
    }).then(function () {
      return shas;
    }).catch(function (e) {
      // Jemand anderes hat gerade gespeichert: einmal neu aufsetzen.
      if (versuch < 3 && (e.status === 422 || e.status === 409)) return commit(dateien, nachricht, versuch + 1);
      throw e;
    });
  }

  // Blob-sha einer Datei im Stand ref (Zweig oder Commit); null = gibt es dort nicht.
  function shaIm(pfad, ref) {
    return api('/contents/' + pfad + '?ref=' + ref).then(function (j) { return j.sha; }, function (e) {
      if (e.status === 404) return null;
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
    if (!verlassenErlaubt()) return;
    ohneWarnung = true;   // die Rückfrage kam gerade schon
    try { sessionStorage.removeItem(SPEICHER); localStorage.removeItem(SPEICHER); } catch (e) {}
    schluessel = null;
    location.hash = '';
    location.reload();
  }

  // ---------------------------------------------------------------- Ansichten
  function zeige(name) {
    $$('[data-ansicht]').forEach(function (el) { el.hidden = el.dataset.ansicht !== name; });
    if (name !== 'bearbeiten') editorHash = null;
    window.scrollTo(0, 0);
  }

  // Bugjagd 10.11.2026 A2-2: Jeder Wechsel der Ansicht läuft über den Hash („Zurück zur Liste“,
  // „Beiträge“, „Neuer Beitrag“, Browser-Zurück). Steht im Editor Ungespeichertes, wird vorher
  // gefragt. Bei „Abbrechen“ kommt der Hash des Editors zurück, OHNE den Editor neu zu füllen.
  function beimHashwechsel() {
    var h = location.hash.replace('#', '');
    if (editorHash !== null) {
      if (h === editorHash) return;                 // unser eigenes Zurücksetzen (oder nichts geändert)
      if (!verlassenErlaubt()) { location.hash = editorHash; return; }
    }
    route();
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
        (d.entwurf || istGeplant(d) ? '' : '<a class="klein-knopf" target="_blank" rel="noopener" style="display:inline-flex;align-items:center;text-decoration:none" href="' + SEITE + 'seiten/beitrag-' + b.slug + '.html">Ansehen</a>') +
        '</div>';
      $('b', li).textContent = d.titel || 'Ohne Titel';
      $('small', li).textContent = datumDe(d.datum) + ' · ' + (d.rubrik || 'News');
      if (d.entwurf) { var m = document.createElement('span'); m.className = 'marke'; m.textContent = 'Entwurf'; $('b', li).appendChild(m); }
      else if (istGeplant(d)) { var g = document.createElement('span'); g.className = 'marke geplant'; g.textContent = 'Geplant ' + planText(d.geplant); $('b', li).appendChild(g); }
      else { li.dataset.pruefen = b.slug; }
      ul.appendChild(li);
    });
    pruefeOnline(0);
  }

  // ---------------------------------------------------------------- Online-Kontrolle
  // Jeder veröffentlichte Beitrag wird auf der echten Website abgerufen: Seite da und Titel aktuell
  // = grün „Online“. Noch nicht da (Seite wird gebaut) = gelb, dann alle 20 Sekunden erneut prüfen.
  var pruefZeit = null;
  function seitenTitel(html) {
    var m = html.match(/<title>([\s\S]*?)<\/title>/i);
    if (!m) return '';
    var t = document.createElement('textarea');
    t.innerHTML = m[1];
    return t.value.replace(/\s+·\s+1\. SC 1911 Heiligenstadt\s*$/, '').trim();
  }
  function setzeMarke(li, art, text, hinweis) {
    var m = li.querySelector('.marke.online, .marke.unterwegs, .marke.fehlt');
    if (!m) { m = document.createElement('span'); $('b', li).appendChild(m); }
    m.className = 'marke ' + art;
    m.textContent = text;
    m.title = hinweis || '';
  }
  function pruefeOnline(runde) {
    clearTimeout(pruefZeit);
    var offen = Array.prototype.slice.call(document.querySelectorAll('[data-liste] li[data-pruefen]')).slice(0, 25);
    if (!offen.length) return;
    var uhr = new Date().toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit' });
    Promise.all(offen.map(function (li) {
      var b = beitraege.filter(function (x) { return x.slug === li.dataset.pruefen; })[0];
      if (!b) return Promise.resolve(true);
      // Anhang ?pruefung=…: am Zwischenspeicher von GitHub Pages vorbei (sonst bis zu 10 Minuten alter Stand)
      return fetch(SEITE + 'seiten/beitrag-' + b.slug + '.html?pruefung=' + Date.now(), { cache: 'no-store' }).then(function (r) {
        if (r.status === 404) return null;
        if (!r.ok) throw new Error(r.status);
        return r.text();
      }).then(function (html) {
        if (html === null) {
          setzeMarke(li, 'unterwegs', 'Wird veröffentlicht …', 'Die Seite ist noch nicht online (Seitenbau läuft). Geprüft ' + uhr + ' Uhr.');
          return false;
        }
        if (seitenTitel(html) !== (b.daten.titel || '').trim()) {
          setzeMarke(li, 'unterwegs', 'Änderung wird veröffentlicht …', 'Online steht noch die vorige Fassung. Geprüft ' + uhr + ' Uhr.');
          return false;
        }
        setzeMarke(li, 'online', '✓ Online', 'Auf der Website geprüft um ' + uhr + ' Uhr.');
        delete li.dataset.pruefen;
        return true;
      }).catch(function () { return true; }); // Website nicht erreichbar (z. B. lokal): keine Marke
    })).then(function (ergebnisse) {
      // Was noch fehlt: weiter prüfen (bis etwa 15 Minuten)
      if (ergebnisse.some(function (x) { return x === false; }) && runde < 45) {
        pruefZeit = setTimeout(function () { pruefeOnline(runde + 1); }, 20000);
      } else if (runde >= 45) {
        document.querySelectorAll('[data-liste] li[data-pruefen] .marke.unterwegs').forEach(function (m) {
          m.className = 'marke fehlt';
          m.textContent = 'Nicht online – bitte melden';
        });
      }
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
    var geplant = istGeplant(d);
    form.planen.checked = geplant;
    form.plan_datum.value = geplant ? d.geplant.slice(0, 10) : '';
    form.plan_zeit.value = geplant ? d.geplant.slice(11, 16) : '18:00';
    zeigePlanung();
    textfeld.innerHTML = d.text || '';
    titelbild = d.bild || null;
    galerie = (d.galerie || []).slice();
    spielSetzen(d.spiel || {});
    form.spiel_slug.dataset.wert = d.spiel_slug || '';
    zeichneSpielwahl();
    zeichneBilder();
    unberuehrt = null;
    $('[data-vorlagewahl]').value = '';
    zeichneVorlagen();
    $('[data-loeschen]').hidden = !b;
    zeigeSpieldaten();
    zeigeSpielwahl();
    zeichneVorberichte();
    if (!beitraege.length) ladeListe().then(zeichneVorberichte);
    meldung('', '');
    aktualisiereKnopf();
    zeige('bearbeiten');
    // Aus dem Feld zurückgelesen, nicht aus den Daten: der Browser schreibt innerHTML beim Setzen um.
    gesichert = editorStand();
    editorHash = b ? 'bearbeiten/' + b.slug : 'neu';
    setTimeout(function () { form.titel.focus(); }, 50);
  }

  // ---------------------------------------------------------------- Ungespeichertes (A2-2)
  var gesichert = null;     // editorStand() beim Öffnen bzw. nach dem letzten Speichern
  var editorHash = null;    // Hash, unter dem der offene Editor steht; null = kein Editor offen
  var ohneWarnung = false;  // Abmelden hat schon gefragt
  function editorStand() {
    return [form.titel.value, form.teaser.value, textfeld.innerHTML, form.datum.value, form.rubrik.value,
      form.entwurf.checked ? '1' : '0', titelbild || '', galerie.join('|'), JSON.stringify(spielFelder()),
      form.planen.checked ? form.plan_datum.value + 'T' + form.plan_zeit.value : '',
      form.rubrik.value === 'Vorbericht' ? (form.spiel_slug.dataset.wert || '') : ''].join('\u0001');
  }
  function ungesichert() {
    if (editorHash === null) return false;
    if (Object.keys(neueBilder).length) return true;
    // Neuer Beitrag: leer oder nur eine unberührte Vorlage ist nichts, was verloren ginge.
    if (!aktuell) return !!titelbild || !!wappen || galerie.length > 0 || !istUnberuehrt() ||
      (form.rubrik.value === 'Spielbericht' && SPIELFELDER.some(function (n) { return n !== 'ort_art' && n !== 'mannschaft' && form['sp_' + n].value.trim(); }));
    return editorStand() !== gesichert;
  }
  function verlassenErlaubt() {
    return !ungesichert() || window.confirm('Der Beitrag hat ungespeicherte Änderungen.\n\nOK = verlassen, die Änderungen gehen verloren.\nAbbrechen = im Beitrag bleiben.');
  }

  // ---------------------------------------------------------------- Veröffentlichung planen
  // Gespeichert als "geplant": "JJJJ-MM-TTTHH:MM" (deutsche Zeit). Der Seitenbau zeigt den Beitrag erst ab dann;
  // .github/workflows/geplant.yml stellt die Seite zum Termin neu online.
  function jetztLokal() { var d = new Date(); return new Date(d - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16); }
  function istGeplant(d) { return !!(d && d.geplant && !d.entwurf && d.geplant > jetztLokal()); }
  function planText(iso) { return datumDe(iso.slice(0, 10)).slice(0, 6) + ' ' + iso.slice(11, 16) + ' Uhr'; }
  function zeigePlanung() {
    $('[data-planenzeit]').hidden = !form.planen.checked;
    $('[data-planenknopf]').hidden = form.planen.checked;
    if (form.planen.checked && !form.plan_datum.value) {
      var morgen = new Date(Date.now() + 864e5);
      form.plan_datum.value = new Date(morgen - morgen.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
    }
    aktualisiereKnopf();
  }
  form.planen.addEventListener('change', zeigePlanung);
  // Eigener Knopf unter „Veröffentlichen“: schaltet die Planung ein und springt zu Datum/Uhrzeit
  $('[data-planenknopf]').addEventListener('click', function () {
    form.planen.checked = true;
    form.entwurf.checked = false;
    zeigePlanung();
    aktualisiereKnopf();
    form.plan_datum.scrollIntoView({ block: 'center', behavior: 'smooth' });
    setTimeout(function () { form.plan_datum.focus(); }, 300);
  });
  [form.plan_datum, form.plan_zeit].forEach(function (f) { f.addEventListener('change', aktualisiereKnopf); });

  function aktualisiereKnopf() {
    $('[data-speichern]').textContent = form.entwurf.checked ? 'Entwurf speichern'
      : form.planen.checked ? 'Planen' : (aktuell ? 'Änderungen veröffentlichen' : 'Veröffentlichen');
  }
  form.entwurf.addEventListener('change', aktualisiereKnopf);

  function zeichneBilder() {
    var tb = $('[data-titelbild]');
    tb.innerHTML = titelbild ? '<img alt="" src="' + rohUrl(titelbild) + '">' : '<p>Noch kein Bild</p>';
    $('[data-titelweg]').hidden = !titelbild;
    var wb = $('[data-wappenbild]');
    wb.innerHTML = wappen ? '<img alt="" src="' + rohUrl(wappen) + '">' : '<img alt="" src="../assets/wappen-leer.svg">';
    $('[data-wappenweg]').hidden = !wappen;
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
          // Spielbericht: ohne Titelbild wird das erste Bild automatisch zum Titelbild
          if (form.rubrik.value === 'Spielbericht' && !titelbild) titelbild = pfad;
          else galerie.push(pfad);
          zeichneBilder();
        });
      });
    }, Promise.resolve()).then(function () { meldung('', ''); }).catch(function (err) { meldung(err.message, 'fehler'); });
    e.target.value = '';
  });

  // ---------------------------------------------------------------- Spieldaten (Rubrik „Spielbericht“)
  // Daraus baut werkzeuge/spielbericht.py die Seite im Aufbau von spielbericht-erfurt.html.
  var SPIELFELDER = ['gegner', 'ort_art', 'wettbewerb', 'runde', 'spieldatum', 'anstoss', 'spielort', 'autor',
    'end_sch', 'end_geg', 'hz_sch', 'hz_geg', 'tore_sch', 'tore_geg', 'karten_sch', 'karten_geg',
    'aufstellung_sch', 'aufstellung_geg', 'zuschauer', 'schiedsrichter', 'vorbericht', 'ticker', 'ticker_link', 'stimmen',
    'kurztitel', 'trainer', 'mannschaft'];
  var wappen = null;
  var vorberichtWahl = $('[data-vorberichtwahl]');

  function spielFelder() {
    var sp = {};
    SPIELFELDER.forEach(function (n) { sp[n] = (form['sp_' + n].value || '').trim(); });
    sp.wappen = wappen || '';
    return sp;
  }
  function spielSetzen(sp) {
    SPIELFELDER.forEach(function (n) { form['sp_' + n].value = sp[n] || ''; });
    if (!form.sp_ort_art.value) form.sp_ort_art.value = 'heim';
    form.sp_mannschaft.dataset.hand = sp.mannschaft ? '1' : '';
    if (!form.sp_mannschaft.value) form.sp_mannschaft.value = 'm1';
    $('[data-mannschafterkannt]').hidden = true;
    zeigeMannschaft();
    wappen = sp.wappen || null;
    vorberichtWahl.dataset.wert = sp.vorbericht || '';
  }
  function zeigeSpieldaten() {
    $('[data-spieldaten]').hidden = form.rubrik.value !== 'Spielbericht';
    $('[data-sbbildtipp]').hidden = form.rubrik.value !== 'Spielbericht';
  }
  form.rubrik.addEventListener('change', zeigeSpieldaten);

  // Mannschaft: Nachwuchs ohne Vorbericht; 2. Mannschaft auswärts = schlanke Seite (werkzeuge/spielbericht.py)
  function zeigeMannschaft() {
    var m = form.sp_mannschaft.value || 'm1';
    $('[data-vorberichtfeld]').hidden = m !== 'm1' && m !== 'm2';
    $('[data-schlanktipp]').hidden = !(m === 'm2' && form.sp_ort_art.value === 'auswaerts');
  }
  [form.sp_mannschaft, form.sp_ort_art].forEach(function (f) { f.addEventListener('change', zeigeMannschaft); });

  // Mannschaft automatisch erkennen: Spieltag + Gegner gegen die Spiele aller Mannschaften
  // (assets/vereinsspiele.json aus dem Seitenbau). Ohne Spieltag: Spiel gegen den Gegner bis 9 Tage
  // vor dem Beitragsdatum (z. B. Nachwuchsbericht am Montag). Von Hand gewählt hat Vorrang.
  var vereinsspiele = null;
  var ALLGEMEIN = ['blau', 'weiß', 'weiss', 'gelb', 'grün', 'gruen', 'schwarz', 'rote', 'stein', 'eintracht', 'union',
    'einheit', 'fortuna', 'germania', 'borussia', 'sportfreunde', 'verein', 'sport', 'stadt', 'preußen', 'preussen',
    'wacker', 'concordia', 'viktoria', 'victoria', 'rotation', 'motor', 'empor', 'aufbau'];
  function worte(name) {
    return (name || '').toLowerCase().split(/[\s\/\-.]+/).filter(function (w) {
      return w.length > 3 && !/^\d+$/.test(w) && ALLGEMEIN.indexOf(w) < 0;
    });
  }
  function ladeVereinsspiele() {
    if (vereinsspiele) return Promise.resolve(vereinsspiele);
    return fetch('../assets/vereinsspiele.json', { cache: 'no-cache' })
      .then(function (r) { return r.ok ? r.json() : []; })
      .catch(function () { return []; })
      .then(function (l) { vereinsspiele = l; return l; });
  }
  function erkenneMannschaft(beimEinfuegen) {
    var hinweis = $('[data-mannschafterkannt]');
    if (form.rubrik.value !== 'Spielbericht' || form.sp_mannschaft.dataset.hand === '1') return;
    var gegner = worte(form.sp_gegner.value);
    if (!gegner.length) { hinweis.hidden = true; return; }
    return ladeVereinsspiele().then(function (liste) {
      var tag = form.sp_spieldatum.value;
      var bis = form.datum.value || new Date().toISOString().slice(0, 10);
      var passend = liste.filter(function (sp) {
        var name = sp.gegner.toLowerCase(), eigene = worte(sp.gegner);
        var gleich = gegner.some(function (w) { return name.indexOf(w) >= 0; }) ||
          eigene.some(function (w) { return form.sp_gegner.value.toLowerCase().indexOf(w) >= 0; });
        if (!gleich) return false;
        if (tag) return sp.datum === tag;
        var tage = (new Date(bis + 'T12:00:00') - new Date(sp.datum + 'T12:00:00')) / 864e5;
        return tage >= 0 && tage <= 9;
      }).sort(function (a, b) { return (b.datum + b.anstoss).localeCompare(a.datum + a.anstoss); });
      if (!passend.length) { hinweis.hidden = true; return; }
      var sp = passend[0];
      form.sp_mannschaft.value = sp.team;
      form.sp_ort_art.value = sp.heim ? 'heim' : 'auswaerts';
      if (!tag) form.sp_spieldatum.value = sp.datum;
      if (!form.sp_anstoss.value) form.sp_anstoss.value = sp.anstoss;
      if (beimEinfuegen === true && !aktuell) form.datum.value = sp.datum;   // neuer Bericht steht beim Spieltag
      var datum = sp.datum.slice(8, 10) + '.' + sp.datum.slice(5, 7) + '.';
      hinweis.textContent = 'Automatisch erkannt: ' + sp.mannschaft + ' – ' + (sp.heim ? 'Heimspiel gegen ' : 'auswärts bei ') + sp.gegner +
        ' am ' + datum + (passend.length > 1 ? ' (mehrere Spiele passen – bitte prüfen)' : '');
      hinweis.hidden = false;
      zeigeMannschaft();
      zeichneVorberichte();
      aktualisiereKnopf();
    });
  }
  form.sp_mannschaft.addEventListener('change', function () {
    form.sp_mannschaft.dataset.hand = '1';
    $('[data-mannschafterkannt]').hidden = true;
  });
  [form.sp_spieldatum, form.sp_gegner].forEach(function (f) { f.addEventListener('change', erkenneMannschaft); });

  // Vorbericht: „Zu welchem Spiel?“ – kommende Spiele der 1. Mannschaft aus dem Seitenbau
  // (assets/kommende-spiele.json, werkzeuge/spielvorschau.py). Gespeichert als "spiel_slug" (FuPa-Spiel).
  var spielWahl = form.spiel_slug;
  var kommendeSpiele = null;
  function ladeSpiele() {
    if (kommendeSpiele) return Promise.resolve(kommendeSpiele);
    return fetch('../assets/kommende-spiele.json', { cache: 'no-cache' })
      .then(function (r) { return r.ok ? r.json() : []; })
      .catch(function () { return []; })
      .then(function (l) { kommendeSpiele = l; return l; });
  }
  function spielText(sp) {
    var d = new Date(sp.anstoss);
    var tag = d.toLocaleDateString('de-DE', { weekday: 'short', day: '2-digit', month: '2-digit', timeZone: 'Europe/Berlin' });
    var zeit = d.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Berlin' });
    var wir = sp.mannschaft === '2. Mannschaft' ? 'SCH II' : 'SCH';
    return tag + ' ' + zeit + ' · ' + (sp.heim ? wir + ' – ' + sp.gegner : sp.gegner + ' – ' + wir) + (sp.wettbewerb ? ' (' + sp.wettbewerb + ')' : '');
  }
  function zeichneSpielwahl() {
    var wert = spielWahl.dataset.wert || '';
    spielWahl.innerHTML = '';
    spielWahl.appendChild(new Option('Automatisch (nach Gegner und Datum)', ''));
    (kommendeSpiele || []).forEach(function (sp) { spielWahl.appendChild(new Option(spielText(sp), sp.slug)); });
    if (wert && !(kommendeSpiele || []).some(function (sp) { return sp.slug === wert; })) {
      var m = wert.match(/-(\d{2})(\d{2})(\d{2})$/);
      spielWahl.appendChild(new Option('Spiel vom ' + (m ? m[3] + '.' + m[2] + '.20' + m[1] : wert) + ' (schon gespielt)', wert));
    }
    spielWahl.value = wert;
  }
  function zeigeSpielwahl() {
    var an = form.rubrik.value === 'Vorbericht';
    $('[data-spielwahl]').hidden = !an;
    if (an) ladeSpiele().then(zeichneSpielwahl);
  }
  spielWahl.addEventListener('change', function () { spielWahl.dataset.wert = spielWahl.value; aktualisiereKnopf(); });
  form.rubrik.addEventListener('change', zeigeSpielwahl);

  // Vorbericht-Auswahl: „automatisch“ nimmt den neuesten Vorbericht bis 10 Tage vor dem Spiel
  function autoVorbericht() {
    var tag = form.sp_spieldatum.value || form.datum.value;
    if (!tag) return null;
    var bis = new Date(tag + 'T12:00:00');
    var gegner = form.sp_gegner.value.trim().toLowerCase().split(/\s+/).filter(function (w) { return w.length > 3; });
    // Einem Spiel zugeordnete Vorberichte („Zu welchem Spiel?“) gelten nur für dieses Spiel
    var zugeordnet = beitraege.filter(function (b) {
      var m = (b.daten.spiel_slug || '').match(/-(\d{2})(\d{2})(\d{2})$/);
      return b.daten.rubrik === 'Vorbericht' && !b.daten.entwurf && m && '20' + m[1] + '-' + m[2] + '-' + m[3] === tag;
    });
    if (zugeordnet.length) return zugeordnet.sort(function (a, b) {
      return (b.daten.datum + (b.daten.zeit || '')).localeCompare(a.daten.datum + (a.daten.zeit || ''));
    })[0];
    var passend = beitraege.filter(function (b) {
      var d = b.daten, tage = (bis - new Date(d.datum + 'T12:00:00')) / 864e5;
      return d.rubrik === 'Vorbericht' && !d.entwurf && !d.spiel_slug && tage >= 0 && tage <= 10;
    });
    var mitName = passend.filter(function (b) {
      var t = ((b.daten.titel || '') + ' ' + (b.daten.text || '')).toLowerCase();
      return gegner.some(function (w) { return t.indexOf(w) >= 0; });
    });
    passend = (gegner.length && mitName.length ? mitName : passend).sort(function (a, b) {
      return (b.daten.datum + (b.daten.zeit || '')).localeCompare(a.daten.datum + (a.daten.zeit || ''));
    });
    return passend[0] || null;
  }
  function zeichneVorberichte() {
    var wert = vorberichtWahl.dataset.wert || '';
    var auto = autoVorbericht();
    vorberichtWahl.innerHTML = '';
    vorberichtWahl.appendChild(new Option('Automatisch' + (auto ? ': „' + auto.daten.titel + '“ (' + datumDe(auto.daten.datum) + ')' : ' (zurzeit keiner passend)'), ''));
    vorberichtWahl.appendChild(new Option('Kein Vorbericht', '-'));
    beitraege.filter(function (b) { return b.daten.rubrik === 'Vorbericht' && !b.daten.entwurf; }).forEach(function (b) {
      vorberichtWahl.appendChild(new Option(datumDe(b.daten.datum) + ' · ' + (b.daten.titel || b.slug), b.slug));
    });
    if (wert && wert !== '-' && !beitraege.some(function (b) { return b.slug === wert; })) {
      vorberichtWahl.appendChild(new Option('(nicht mehr vorhanden) ' + wert, wert));
    }
    vorberichtWahl.value = wert;
  }
  vorberichtWahl.addEventListener('change', function () { vorberichtWahl.dataset.wert = vorberichtWahl.value; });
  [form.sp_spieldatum, form.sp_gegner, form.datum].forEach(function (f) { f.addEventListener('change', zeichneVorberichte); });

  $('[data-wappendatei]').addEventListener('change', function (e) {
    var datei = e.target.files[0];
    if (!datei) return;
    bildVerkleinern(datei).then(function (b) {
      var pfad = neuerBildpfad(b.endung);
      neueBilder[pfad] = b.base64;
      wappen = pfad;
      zeichneBilder();
    }).catch(function (err) { meldung(err.message, 'fehler'); });
    e.target.value = '';
  });
  $('[data-wappenweg]').addEventListener('click', function () { wappen = null; zeichneBilder(); });

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

  // ---------------------------------------------------------------- Spielbericht einfügen und selbst aufteilen
  // Erkennt den fertigen Bericht (Überschrift, Kurzüberschrift, Einstieg, Zwischenüberschriften,
  // Absätze, Block „Spieldaten“) und verteilt ihn auf Titel, Anreißer, Text und Spieldaten-Felder.
  function escHtml(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function zeilenAus(t) {
    return t.replace(/\r/g, '').split('\n').map(function (z) {
      var roh = z.trim(), kopf = false;
      if (/^#{1,6}\s+/.test(roh)) { kopf = true; roh = roh.replace(/^#{1,6}\s+/, ''); }
      if (/^\*\*[^*]+\*\*:?$/.test(roh) || /^__[^_]+__$/.test(roh)) { kopf = true; }
      roh = roh.replace(/\*\*|__/g, '').replace(/^\s*[-*]\s+(?=\S)/, '').trim();
      return { text: roh, kopf: kopf };
    });
  }
  function istSpieldatenZeile(z) { return /^spieldaten:?$/i.test(z.text); }
  function istSch(name) { return /heiligenstadt|^sch\b/i.test(name); }

  function spieldatenLesen(zeilen) {
    var sp = {}, kopf = null, teams = null, abschnitt = null, werte = {};
    zeilen.forEach(function (z) {
      var t = z.text;
      if (!t) return;
      if (!kopf) {
        var m = t.match(/^(.+?)\s+[-–—]\s+(.+?)\s+(\d+)\s*:\s*(\d+)(?:\s*\(\s*(\d+)\s*:\s*(\d+)\s*\))?\s*$/);
        if (m) { kopf = m; teams = [m[1].trim(), m[2].trim()]; return; }
      }
      var label = t.replace(/:$/, '');
      var bekannt = { 'schiedsrichter': 'schiri', 'zuschauer': 'zuschauer', 'zuschauerzahl': 'zuschauer', 'tore': 'tore',
        'trainer': 'trainer', 'rote karte': 'rot', 'rote karten': 'rot', 'gelb-rote karte': 'rot', 'gelb-rote karten': 'rot' }[label.toLowerCase()];
      if (bekannt) { abschnitt = bekannt; return; }
      if (teams && (label === teams[0] || label === teams[1])) { abschnitt = label === teams[0] ? 'elf0' : 'elf1'; return; }
      // „Schiedsrichter: Name“ in einer Zeile
      var inline = t.match(/^(Schiedsrichter|Zuschauer(?:zahl)?|Tore|Trainer)\s*:\s*(.+)$/i);
      if (inline) {
        abschnitt = { sc: 'schiri', zu: 'zuschauer', to: 'tore', tr: 'trainer' }[inline[1].slice(0, 2).toLowerCase()];
        t = inline[2];
      }
      if (abschnitt) werte[abschnitt] = (werte[abschnitt] ? werte[abschnitt] + ' ' : '') + t;
    });
    if (!kopf) return null;
    var schHeim = istSch(teams[0]) || !istSch(teams[1]);
    sp.ort_art = schHeim ? 'heim' : 'auswaerts';
    sp.gegner = schHeim ? teams[1] : teams[0];
    var sch = schHeim ? 0 : 1;
    function paar(a, b) { return sch === 0 ? [a, b] : [b, a]; }
    var end = paar(kopf[3], kopf[4]);
    sp.end_sch = end[0]; sp.end_geg = end[1];
    if (kopf[5] !== undefined) { var hz = paar(kopf[5], kopf[6]); sp.hz_sch = hz[0]; sp.hz_geg = hz[1]; }
    sp.aufstellung_sch = werte[sch === 0 ? 'elf0' : 'elf1'] || '';
    sp.aufstellung_geg = werte[sch === 0 ? 'elf1' : 'elf0'] || '';
    sp.schiedsrichter = werte.schiri || '';
    sp.zuschauer = werte.zuschauer || '';
    sp.trainer = werte.trainer || '';
    // Tore im Vereinsformat („1:0 Wolanski (17.), 1:1 Kurth (31.)“) je Tor eine Zeile; wer getroffen hat,
    // ergibt beim Seitenbau der Spielstand (werkzeuge/spielbericht.py)
    sp.tore_sch = (werte.tore || '').split(/\s*[,;]\s*(?![^()]*\))/).filter(function (x) { return x.trim(); }).join('\n');
    sp.tore_geg = '';
    return sp;
  }

  function spielberichtZerlegen(roh) {
    var zeilen = zeilenAus(roh);
    var i = zeilen.findIndex(istSpieldatenZeile);
    var artikelZ = (i >= 0 ? zeilen.slice(0, i) : zeilen).filter(function (z) { return z.text; });
    var daten = i >= 0 ? spieldatenLesen(zeilen.slice(i + 1)) : null;
    if (artikelZ.length < 3) return null;
    var aus = { titel: artikelZ[0].text, kurz: '', teaser: '', html: '', spiel: daten };
    var rest = artikelZ.slice(1);
    // Kurzüberschrift: kurze Zeile direkt unter der Überschrift
    if (rest.length > 1 && rest[0].text.length <= 24 && !/\.$/.test(rest[0].text)) aus.kurz = rest.shift().text;
    function istKopf(z, naechste) {
      if (z.kopf) return true;
      return z.text.length <= 90 && !/[.!?:;,“"…)]$/.test(z.text) && !!naechste && naechste.text.length > z.text.length;
    }
    // Einstieg vor der ersten Zwischenüberschrift = Anreißer
    if (rest.length && !istKopf(rest[0], rest[1])) aus.teaser = rest.shift().text;
    var html = '';
    // Langer Einstieg: ganz in den Text, als Anreißer nur die ersten Sätze (max. 300 Zeichen)
    if (aus.teaser.length > 300) {
      html += '<p>' + escHtml(aus.teaser) + '</p>';
      var saetze = aus.teaser.match(/[^.!?]+[.!?]+(\s|$)/g) || [aus.teaser], kurzT = '';
      saetze.forEach(function (s) { if ((kurzT + s).trim().length <= 300) kurzT += s; });
      aus.teaser = kurzT.trim() || aus.teaser.slice(0, 297).replace(/\s+\S*$/, '') + ' …';
    }
    // Was im Fließtext steht, für die Spieldaten nutzen: Spieltag, Liga, Stadion, Trainerzitat
    var alles = artikelZ.map(function (z) { return z.text; }).join('\n');
    var extra = {}, m;
    if ((m = alles.match(/(\d{1,2})\.\s*Spieltag\s+(?:der|in der|im)\s+([A-ZÄÖÜ][\wäöüß-]+(?:-[A-ZÄÖÜ][\wäöüß]+)?)/))) {
      extra.runde = m[1] + '. Spieltag'; extra.wettbewerb = m[2];
    }
    if ((m = alles.match(/\b(?:im|auf dem|in der)\s+([A-ZÄÖÜ][\wäöüß-]*(?:stadion|sportplatz|sportpark|arena|kampfbahn|sportfeld))\b/i))) extra.spielort = m[1];
    if ((m = alles.match(/Trainer(?:in)?\s+((?:\[[^\]]+\]\s+)?[A-ZÄÖÜ][\wäöüß-]+(?:\s+[A-ZÄÖÜ][\wäöüß-]+)?)[^„\n]{0,40}„([^“\n]+)“/))) {
      extra.stimmen = m[1] + ' | Trainer | ' + m[2];
    }
    aus.extra = extra;
    rest.forEach(function (z, k) {
      // Schlusssatz mit Rückfrage nach fehlenden Angaben gehört nicht in den Bericht
      if (k === rest.length - 1 && /fehl(en|t)\b.*\?$/i.test(z.text)) return;
      html += istKopf(z, rest[k + 1]) ? '<h3>' + escHtml(z.text) + '</h3>' : '<p>' + escHtml(z.text) + '</p>';
    });
    aus.html = html;
    return aus;
  }

  function spielberichtEinsetzen(t) {
    var r = spielberichtZerlegen(t);
    if (!r) return false;
    form.rubrik.value = 'Spielbericht';
    form.rubrik.dispatchEvent(new Event('change'));
    form.titel.value = r.titel;
    if (r.teaser) form.teaser.value = r.teaser;
    textfeld.innerHTML = r.html;
    form.sp_kurztitel.value = r.kurz;
    if (r.spiel) Object.keys(r.spiel).forEach(function (n) { if (form['sp_' + n]) form['sp_' + n].value = r.spiel[n]; });
    // Spieltag, Liga, Stadion, Zitat aus dem Text nur eintragen, wo noch nichts steht
    Object.keys(r.extra).forEach(function (n) { if (form['sp_' + n] && !form['sp_' + n].value.trim()) form['sp_' + n].value = r.extra[n]; });
    var teile = ['Titel', r.kurz && 'Kurzüberschrift', r.teaser && 'Anreißer', 'Text', r.spiel && 'Spieldaten'].filter(Boolean);
    function fertig(zusatz) {
      var fehlt = ['gegner', 'end_sch', 'wettbewerb', 'runde', 'spielort'].filter(function (n) { return !String(form['sp_' + n].value).trim(); })
        .map(function (n) { return { gegner: 'Gegner', end_sch: 'Ergebnis', wettbewerb: 'Wettbewerb', runde: 'Spieltag', spielort: 'Spielort' }[n]; });
      meldung('Spielbericht erkannt und aufgeteilt: ' + teile.join(', ') + (zusatz && zusatz.length ? '; aus dem Text erkannt: ' + zusatz.join(', ') : '') +
        '. Bitte kurz prüfen' + (fehlt.length ? '; noch offen: ' + fehlt.join(', ') : '') + '.', 'ok');
    }
    var liga = t.match(LIGEN);
    if (liga && !form.sp_wettbewerb.value.trim()) form.sp_wettbewerb.value = liga[1];
    if (r.spiel && r.spiel.gegner) {
      if (r.spiel.spieldatum && !aktuell) form.datum.value = r.spiel.spieldatum;
      erkenneMannschaft(true);
      zeichneVorberichte();
      aktualisiereKnopf();
      fertig();
    } else {
      fertig();
      fliesstextAuswerten(t).then(function (x) { fertig(x.teile); }, function () {});
    }
    return true;
  }

  // ---------------------------------------------------------------- Spiel aus dem Fließtext erkennen (16.11.2026)
  // Ohne Block „Spieldaten“: Mannschaft, Spiel, Ergebnis und Wettbewerb aus dem Text selbst ableiten.
  // Grundlage ist der Vereinsspielplan aller Mannschaften (assets/vereinsspiele.json); Trainer-Elf, Liga
  // und Altersklasse grenzen die Mannschaft ein, der Gegnername im Text das Spiel.
  var TRAINER_ELF = { ludwig: 'm1', papst: 'm2', hartmann: 'u19-1', 'förster': 'u17-1', foerster: 'u17-1',
    perriello: 'u17-2', eschborn: 'u15-1', seipel: 'u13-1' };
  var LIGA_TEAM = [[/thüringenliga|verbandsliga/i, 'm1'], [/kreisoberliga/i, 'm2']];
  var LIGEN = /\b(Thüringenliga|Verbandsliga|Landesliga|Landesklasse|Kreisoberliga|Kreisliga|Kreisklasse|Talenteliga|Regionalliga|Oberliga|Kreispokal|Landespokal|Thüringenpokal|Hallenmasters|Hallenturnier|Testspiel|Freundschaftsspiel)\b/;
  var JUNIOREN = { a: 'u19-1', b1: 'u17-1', b: 'u17-1', b2: 'u17-2', c: 'u15-1', c1: 'u15-1', d1: 'u13-1' };

  function mannschaftsHinweise(text) {
    var tipps = {}, m, re = /\b([A-ZÄÖÜ][a-zäöüß]+)-Elf\b/g;
    while ((m = re.exec(text))) { var t = TRAINER_ELF[m[1].toLowerCase()]; if (t) tipps[t] = (tipps[t] || 0) + 3; }
    LIGA_TEAM.forEach(function (l) { if (l[0].test(text)) tipps[l[1]] = (tipps[l[1]] || 0) + 2; });
    re = /\b([A-D])([12])?-Junioren\b/g;
    while ((m = re.exec(text))) {
      var j = JUNIOREN[(m[1] + (m[2] || '')).toLowerCase()] || JUNIOREN[m[1].toLowerCase()];
      if (j) tipps[j] = (tipps[j] || 0) + 3;
    }
    // „Trainer Andreas Seipel“ ohne „-Elf“
    Object.keys(TRAINER_ELF).forEach(function (n) {
      if (new RegExp('Trainer(?:in)?\\s+(?:[A-ZÄÖÜ][a-zäöüß]+\\s+)?' + n, 'i').test(text)) tipps[TRAINER_ELF[n]] = (tipps[TRAINER_ELF[n]] || 0) + 2;
    });
    return tipps;
  }

  // Ergebnis „4:0 (1:0)“ aus Sicht des SCH; Uhrzeiten („14:00 Uhr“) zählen nicht
  function ergebnisAusText(text) {
    var re = /(\d{1,2})\s*:\s*(\d{1,2})(?:\s*\(\s*(\d{1,2})\s*:\s*(\d{1,2})\s*\))?(?!\s*Uhr)(?!\d)/g, m, alle = [];
    while ((m = re.exec(text))) {
      var davor = text.slice(Math.max(0, m.index - 3), m.index);
      if (/\d[.:]\s*$/.test(davor) || /(?:^|\D)\(\s*$/.test(davor)) continue;   // Datum/Uhrzeit oder Halbzeitstand
      if (+m[1] > 30 || +m[2] > 30) continue;
      alle.push(m);
    }
    if (!alle.length) return null;
    // Das zuerst genannte Ergebnis zählt (Einstieg); den Halbzeitstand liefert notfalls eine spätere Nennung
    var beste = alle[0], a = +beste[1], b = +beste[2], h = null;
    alle.some(function (x) {
      var gleich = (+x[1] === a && +x[2] === b) || (+x[1] === b && +x[2] === a);
      if (gleich && x[3] !== undefined) { h = +x[1] === a ? [+x[3], +x[4]] : [+x[4], +x[3]]; return true; }
      return false;
    });
    var satz = (text.slice(Math.max(0, beste.index - 220), beste.index + 120).match(/[^.!?]*$/) || [''])[0] +
      text.slice(beste.index, beste.index + 160);
    var drehen = false;
    if (/aus sicht (?:der|des) (?:gäste|gegner)/i.test(satz)) drehen = true;
    else if (!/aus sicht/i.test(satz)) {
      if (/\b(gewinn|gewann|siegt|besiegt|sieg\b|erfolg|dreier|bezwing)/i.test(satz) && a < b) drehen = true;
      if (/\b(verlier|verlor|unterl[ai]g|niederlage|pleite)/i.test(satz) && a > b) drehen = true;
    }
    if (drehen) { var x = a; a = b; b = x; if (h) h = [h[1], h[0]]; }
    return { sch: a, geg: b, hz: h };
  }

  function spielAusText(text) {
    return ladeVereinsspiele().then(function (liste) {
      if (!liste.length) return null;
      var tipps = mannschaftsHinweise(text), klein = text.toLowerCase();
      var bis = form.datum.value || new Date().toISOString().slice(0, 10);
      var genannt = (text.match(/\b(\d{1,2})\.(\d{1,2})\.(?:(20\d\d)|\b)/) || null);
      var kandidaten = liste.map(function (sp) {
        var tage = (new Date(bis + 'T12:00:00') - new Date(sp.datum + 'T12:00:00')) / 864e5;
        var p = 0;
        var w = worte(sp.gegner);
        var treffer = w.filter(function (x) { return klein.indexOf(x) >= 0; }).length;
        if (treffer) p += 4 + treffer;
        if (tipps[sp.team]) p += tipps[sp.team];
        if (genannt && +genannt[1] === +sp.datum.slice(8, 10) && +genannt[2] === +sp.datum.slice(5, 7)) p += 3;
        else if (tage < 0 || tage > 9) p -= 6;
        return { sp: sp, p: p, gegnerTreffer: treffer };
      }).filter(function (k) { return k.gegnerTreffer && k.p > 0; })
        .sort(function (a, b) { return b.p - a.p || (b.sp.datum).localeCompare(a.sp.datum); });
      if (!kandidaten.length) return null;
      return { sp: kandidaten[0].sp, unsicher: kandidaten.length > 1 && kandidaten[1].p === kandidaten[0].p };
    });
  }

  function fliesstextAuswerten(text) {
    var erg = ergebnisAusText(text), liga = text.match(LIGEN);
    return spielAusText(text).then(function (treffer) {
      var teile = [];
      if (treffer) {
        var sp = treffer.sp;
        form.sp_gegner.value = sp.gegner;
        form.sp_mannschaft.value = sp.team;
        form.sp_mannschaft.dataset.hand = '';
        form.sp_ort_art.value = sp.heim ? 'heim' : 'auswaerts';
        form.sp_spieldatum.value = sp.datum;
        if (!form.sp_anstoss.value) form.sp_anstoss.value = sp.anstoss;
        if (!aktuell) form.datum.value = sp.datum;   // Bericht steht in der Liste beim Spieltag
        var hinweis = $('[data-mannschafterkannt]');
        hinweis.textContent = 'Automatisch erkannt: ' + sp.mannschaft + ' – ' + (sp.heim ? 'Heimspiel gegen ' : 'auswärts bei ') +
          sp.gegner + ' am ' + sp.datum.slice(8, 10) + '.' + sp.datum.slice(5, 7) + '.' + (treffer.unsicher ? ' (mehrere Spiele passen – bitte prüfen)' : '');
        hinweis.hidden = false;
        zeigeMannschaft();
        teile.push(sp.mannschaft + ' gegen ' + sp.gegner);
      }
      if (erg && !form.sp_end_sch.value) {
        form.sp_end_sch.value = erg.sch; form.sp_end_geg.value = erg.geg;
        if (erg.hz) { form.sp_hz_sch.value = erg.hz[0]; form.sp_hz_geg.value = erg.hz[1]; }
        teile.push('Ergebnis ' + erg.sch + ':' + erg.geg);
      }
      if (liga && !form.sp_wettbewerb.value.trim()) { form.sp_wettbewerb.value = liga[1]; teile.push(liga[1]); }
      zeichneVorberichte();
      aktualisiereKnopf();
      return { teile: teile, spiel: !!treffer };
    });
  }

  // Sieht der eingefügte Text nach einem Spielbericht aus? (Ergebnis + mehrere Absätze)
  function wieSpielbericht(t) {
    var zeilen = t.split(/\n/).filter(function (z) { return z.trim(); }).length;
    return zeilen >= 4 && !!ergebnisAusText(t);
  }

  // Einfügen nur als reiner Text (kein Word-/Webseiten-Ballast); Absätze bleiben erhalten
  textfeld.addEventListener('paste', function (e) {
    var t = (e.clipboardData || window.clipboardData).getData('text/plain');
    if (!t) return;
    e.preventDefault();
    // Ganzer Spielbericht (Rubrik Spielbericht oder Block „Spieldaten“ dabei): selbst aufteilen
    var zeilenAnzahl = t.split(/\n/).filter(function (z) { return z.trim(); }).length;
    var leer = !textfeld.textContent.trim() || (unberuehrt !== null && stand() === unberuehrt);
    var rubrikPasst = ['Spielbericht', 'News', 'Nachwuchs'].indexOf(form.rubrik.value) >= 0;
    if (zeilenAnzahl >= 4 && (form.rubrik.value === 'Spielbericht' || zeilenAus(t).some(istSpieldatenZeile) ||
        (leer && rubrikPasst && wieSpielbericht(t))) &&
        spielberichtEinsetzen(t)) return;
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
  // Grundvorlagen werden nicht mehr automatisch eingesetzt (Wunsch der Redaktion, 16.11.2026): neue Beiträge starten leer.
  // (der Seitenbau liest nur inhalte/beitraege/). Solange die Datei fehlt, gelten die Grundvorlagen.
  var VORLAGEN = 'inhalte/vorlagen.json';
  var GRUND = [
    { id: 'grund-spielbericht', name: 'Spielbericht', rubrik: 'Spielbericht', standard: false,
      titel: '[Sieg/Remis/Niederlage] gegen [Gegner]',
      teaser: '[Ergebnis in einem Satz: Wer hat wie gespielt?]',
      // Ergebnis, Tore, Aufstellung und Stimmen kommen aus den Spieldaten unter dem Text.
      text: '<p>[Einstieg: Ergebnis, Stimmung, wichtigste Szene]</p>' +
        '<h2>[Überschrift zur 1. Halbzeit]</h2><p>[Wie lief die erste Halbzeit?]</p>' +
        '<h2>[Überschrift zur 2. Halbzeit]</h2><p>[Wie lief die zweite Halbzeit?]</p>' +
        '<h2>Ausblick</h2><p>[Nächstes Spiel: Tag, Datum, Uhrzeit, Gegner, Ort]</p>' },
    { id: 'grund-vorbericht', name: 'Vorbericht', rubrik: 'Vorbericht', standard: false,
      titel: 'Vorschau: SCH gegen [Gegner]',
      teaser: '[Worum geht es am Wochenende?]',
      text: '<h2>Die Ausgangslage</h2><p>[Tabellenplatz, letzte Ergebnisse, Bilanz gegen den Gegner]</p>' +
        '<h2>Personal</h2><p>[Wer fehlt, wer kommt zurück?]</p>' +
        '<h2>Anpfiff</h2><ul><li><b>Wann:</b> [Tag, Datum, Uhrzeit]</li><li><b>Wo:</b> [Sportplatz, Ort]</li><li><b>Eintritt:</b> [Preis]</li></ul>' +
        '<p>[Aufruf an die Fans]</p>' },
    { id: 'grund-nachwuchs', name: 'Nachwuchs', rubrik: 'Nachwuchs', standard: false,
      titel: '[Mannschaft, z. B. D-Jugend]: [Kurzmeldung]',
      teaser: '[Was ist passiert?]',
      text: '<p>[Was ist passiert? Spiel, Turnier, Ausflug …]</p><p>[Besondere Momente, Ergebnisse]</p>' +
        '<h2>Danke</h2><p>[Dank an Trainer, Eltern, Helfer, Sponsoren]</p>' },
    { id: 'grund-verein', name: 'Vereinsnachricht', rubrik: 'Verein', standard: false,
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
    // Nur die Vorlagen der gewählten Rubrik (16.11.2026: andere Rubriken stiften nur Verwirrung)
    var teil = sortiert.filter(function (v) { return v.rubrik === rubrik; });
    vorlageWahl.appendChild(new Option(teil.length ? '– Vorlage einsetzen –' : '– keine Vorlage für ' + rubrik + ' –', ''));
    teil.forEach(function (v) {
      vorlageWahl.appendChild(new Option(v.name + (v.standard ? ' (Standard)' : ''), v.id));
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
    // Unverändertes Gerüst einer anderen Rubrik nicht stehen lassen
    if (!aktuell && unberuehrt !== null && stand() === unberuehrt) {
      form.titel.value = ''; form.teaser.value = ''; textfeld.innerHTML = '';
      unberuehrt = null; vorlageWahl.value = '';
    }
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
    var basis = slugStamm(titel, datum), slug = basis, n = 2;
    while (beitraege.some(function (b) { return b.slug === slug; })) slug = basis + '-' + n++;
    return slug;
  }
  function slugStamm(titel, datum) {
    var s = (titel || 'beitrag').toLowerCase()
      .replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue').replace(/ß/g, 'ss')
      .normalize('NFKD').replace(/[̀-ͯ]/g, '')
      .replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 60).replace(/-+$/, '');
    return datum + '-' + (s || 'beitrag');
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
    var istSpiel = form.rubrik.value === 'Spielbericht';
    if (istSpiel && !form.entwurf.checked && !form.sp_gegner.value.trim() &&
        !window.confirm('Bei den Spieldaten fehlt der Gegner. Ohne Gegner gibt es keine Ergebnisleiste, keine Spielinfo und keinen Liveticker.\n\nTrotzdem veröffentlichen?')) return;
    if (offen.length && !form.entwurf.checked &&
        !window.confirm('Im Beitrag stehen noch Platzhalter aus der Vorlage: ' + offen.slice(0, 5).join(', ') + (offen.length > 5 ? ' …' : '') + '\n\nTrotzdem veröffentlichen?')) return;

    var neu = !aktuell;
    // Planung: Termin prüfen; Datum und Uhrzeit des Beitrags werden der geplante Termin
    var geplant = '';
    if (form.planen.checked && !form.entwurf.checked) {
      if (!form.plan_datum.value || !form.plan_zeit.value) { meldung('Bitte Datum und Uhrzeit für die Veröffentlichung eintragen.', 'fehler'); form.plan_datum.focus(); return; }
      geplant = form.plan_datum.value + 'T' + form.plan_zeit.value;
      if (geplant <= jetztLokal()) {
        if (!window.confirm('Der geplante Zeitpunkt liegt schon in der Vergangenheit.\n\nBeitrag jetzt sofort veröffentlichen?')) return;
        geplant = '';
        form.planen.checked = false;
        zeigePlanung();
      } else {
        form.datum.value = form.plan_datum.value;
      }
    }
    var slug = aktuell ? aktuell.slug : slugAus(titel, form.datum.value);
    var stamm = slugStamm(titel, form.datum.value);
    var geladenSha = aktuell ? aktuell.sha : null;
    var vorher = aktuell ? aktuell.daten : {};
    var daten = {
      titel: titel,
      datum: form.datum.value,
      zeit: geplant ? geplant.slice(11, 16) : (vorher.zeit || new Date().toTimeString().slice(0, 5)),
      rubrik: form.rubrik.value,
      teaser: form.teaser.value.trim(),
      bild: titelbild || '',
      text: text,
      galerie: galerie.slice(),
      entwurf: form.entwurf.checked
    };
    if (geplant) daten.geplant = geplant;
    if (form.rubrik.value === 'Vorbericht' && form.spiel_slug.dataset.wert) daten.spiel_slug = form.spiel_slug.dataset.wert;
    if (istSpiel) daten.spiel = spielFelder();
    var wappenNeu = istSpiel ? (wappen || '') : '';
    var json = textZuBase64(JSON.stringify(daten, null, 2) + '\n');
    var standBeimSpeichern = editorStand();   // was während des Speicherns noch getippt wird, bleibt „ungespeichert“
    var bilder = [];
    Object.keys(neueBilder).forEach(function (pfad) {
      if (pfad === titelbild || pfad === wappenNeu || galerie.indexOf(pfad) >= 0) bilder.push({ pfad: pfad, inhalt: neueBilder[pfad] });
    });
    // Nicht mehr benutzte Bilder dieses Beitrags entfernen
    [vorher.bild, (vorher.spiel || {}).wappen].concat(vorher.galerie || []).forEach(function (p) {
      if (p && p.indexOf(BILDER) === 0 && p !== titelbild && p !== wappenNeu && galerie.indexOf(p) < 0) bilder.push({ pfad: p, inhalt: null });
    });
    // Bugjagd 23.10. DS-F2: geprüft wird gegen den Stand, auf dem der Commit aufbaut.
    // Neuer Beitrag: nie eine vorhandene Datei überschreiben (die Liste ist evtl. nicht geladen
    // oder veraltet), dann „-2“, „-3“ … anhängen. Bearbeiten: Hat jemand anderes die Datei seit
    // dem Laden geändert oder gelöscht, wird nicht gespeichert.
    function konflikt(text) { var e = new Error(text); e.status = 'konflikt'; return e; }
    function freierSlug(k, n, basisSha) {
      if (n > 99) return Promise.reject(new Error('Kein freier Dateiname für diesen Titel gefunden.'));
      return shaIm(ORDNER + k + '.json', basisSha).then(function (sha) {
        return sha ? freierSlug(stamm + '-' + n, n + 1, basisSha) : k;
      });
    }
    var dateien = function (basisSha) {
      var weiter = neu ? freierSlug(slug, 2, basisSha).then(function (k) { slug = k; })
        : shaIm(ORDNER + slug + '.json', basisSha).then(function (sha) {
          if (!geladenSha || sha === geladenSha) return;
          throw konflikt(sha
            ? 'Nicht gespeichert: Dieser Beitrag wurde inzwischen von jemand anderem geändert. Deine Eingaben stehen noch im Formular. Text kopieren, die Liste neu laden, den Beitrag wieder öffnen und die Änderung dort erneut eintragen.'
            : 'Nicht gespeichert: Dieser Beitrag wurde inzwischen von jemand anderem gelöscht. Deine Eingaben stehen noch im Formular. Text kopieren und bei Bedarf als neuen Beitrag anlegen.');
        });
      return weiter.then(function () { return [{ pfad: ORDNER + slug + '.json', inhalt: json }].concat(bilder); });
    };

    var knopf = $('[data-speichern]');
    knopf.disabled = true;
    meldung('Wird gespeichert …', '');
    var art = daten.entwurf ? 'Entwurf' : daten.geplant ? 'Geplant für ' + planText(daten.geplant) : (aktuell ? 'Beitrag geändert' : 'Neuer Beitrag');
    commit(dateien, art + ': ' + titel + ' (Redaktion)').then(function (shas) {
      neueBilder = {};
      var eintrag = { slug: slug, daten: daten, sha: shas[ORDNER + slug + '.json'] };
      beitraege = beitraege.filter(function (b) { return b.slug !== slug; }).concat([eintrag]);
      aktuell = eintrag;
      gesichert = standBeimSpeichern;
      editorHash = 'bearbeiten/' + slug;
      $('[data-loeschen]').hidden = false;
      meldung(daten.entwurf ? 'Entwurf gespeichert.'
        : daten.geplant ? 'Geplant. Der Beitrag erscheint automatisch am ' + planText(daten.geplant) + ' (höchstens etwa 15 bis 20 Minuten später).'
        : 'Gespeichert. Der Beitrag ist in etwa 2 Minuten auf der Seite.', 'ok');
      if (!daten.entwurf && !daten.geplant) zeigeLiveHinweis(slug, titel);
      history.replaceState(null, '', '#bearbeiten/' + slug);
    }).catch(function (err) {
      meldung(err.status === 'konflikt' ? err.message : 'Speichern fehlgeschlagen: ' + err.message, 'fehler');
    }).then(function () { knopf.disabled = false; aktualisiereKnopf(); });
  });

  $('[data-loeschen]').addEventListener('click', function () {
    if (!aktuell) return;
    if (!window.confirm('„' + (aktuell.daten.titel || 'Beitrag') + '“ wirklich löschen? Das lässt sich hier nicht rückgängig machen.')) return;
    var d = aktuell.daten;
    var dateien = [{ pfad: ORDNER + aktuell.slug + '.json', inhalt: null }];
    [d.bild, (d.spiel || {}).wappen].concat(d.galerie || []).forEach(function (p) { if (p && p.indexOf(BILDER) === 0) dateien.push({ pfad: p, inhalt: null }); });
    meldung('Wird gelöscht …', '');
    commit(dateien, 'Beitrag gelöscht: ' + (d.titel || aktuell.slug) + ' (Redaktion)').then(function () {
      var slug = aktuell.slug;
      beitraege = beitraege.filter(function (b) { return b.slug !== slug; });
      aktuell = null;
      editorHash = null;   // gelöscht: nichts mehr zu verlieren, keine Rückfrage
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

  // Vor dem Verlassen warnen, wenn etwas ungespeichert ist (Titel, Text, Anreißer, Bilder …)
  window.addEventListener('beforeunload', function (e) {
    if (!ohneWarnung && ungesichert()) { e.preventDefault(); e.returnValue = ''; }
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
  window.addEventListener('hashchange', beimHashwechsel);

  var gemerkt = null;
  try { gemerkt = sessionStorage.getItem(SPEICHER) || localStorage.getItem(SPEICHER); } catch (e) {}
  if (gemerkt) {
    anmelden(gemerkt, !!(function () { try { return localStorage.getItem(SPEICHER); } catch (e) { return null; } })())
      .then(route)
      .catch(function () { schluessel = null; try { sessionStorage.removeItem(SPEICHER); localStorage.removeItem(SPEICHER); } catch (e) {} route(); });
  } else {
    route();
  }

  // ---------------------------------------------------------------- Vorschau (16.11.2026)
  // Zeigt den Beitrag so, wie ihn der Seitenbau (werkzeuge/beitraege.py, spielbericht.py) erzeugt:
  // gleiche Seitenvorlage, gleiche Stile. Spielberichte mit Kopfbild, Ergebnistafel und Text.
  var vorschauDialog = $('[data-vorschaudialog]');
  var vorschauRahmen = $('[data-vorschaurahmen]');
  var vorschauAnsicht = 'computer';
  var seitenCache = {};
  var BEITRAG_VORLAGE = 'seiten/beitrag-serie-haelt-weiter.html';
  var SB_VORLAGE = 'spielbericht-erfurt.html';
  var WOCHENTAG = ['So', 'Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa'];
  var MONATE = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];

  function holeSeite(pfad) {
    if (seitenCache[pfad]) return Promise.resolve(seitenCache[pfad]);
    return fetch('../' + pfad, { cache: 'no-cache' }).then(function (r) {
      if (!r.ok) throw new Error('Vorlage ' + pfad + ' nicht gefunden');
      return r.text();
    }).then(function (t) { seitenCache[pfad] = t; return t; });
  }
  function eh(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function bildFuer(pfad) { return pfad ? rohUrl(pfad) : new URL('../assets/hero.jpg', location.href).href; }
  // wie beitraege.zwischentitel: fette Zeile am Absatzanfang wird Zwischenüberschrift
  function vorschauText(html) {
    return html.replace(/<p>\s*<(?:strong|b)>([^<]+)<\/(?:strong|b)>\s*(?:<br\s*\/?>\s*((?:(?!<\/p>)[\s\S])*?))?<\/p>/g, function (m, titel, rest) {
      titel = titel.replace(/\u2028/g, ' ').trim();
      if (!titel || titel.length > 110 || /^[„"»“']/.test(titel) || (/[.!?]$/.test(titel) && titel.length > 70)) return m;
      return '<h3>' + titel + '</h3>' + (rest && rest.trim() ? '<p>' + rest.trim() + '</p>' : '');
    });
  }
  function datumLang(iso) {
    var t = (iso || '').split('-');
    return t.length === 3 ? t[2] + '. ' + MONATE[+t[1] - 1] + ' ' + t[0] : '';
  }
  function datumTag(iso) {
    if (!iso) return '';
    var d = new Date(iso + 'T12:00:00');
    return WOCHENTAG[d.getDay()] + ', ' + datumDe(iso);
  }
  function wappenSlug(name) {
    return (name || '').toLowerCase().replace(/ä/g, 'ae').replace(/ö/g, 'oe').replace(/ü/g, 'ue').replace(/ß/g, 'ss')
      .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  }
  // Seitenvorlage nehmen, <main> austauschen, Skripte raus (Vorschau läuft ohne Skripte)
  function seiteMit(vorlage, basis, mainHtml, zusatzCss) {
    var doc = new DOMParser().parseFromString(vorlage, 'text/html');
    var base = doc.createElement('base');
    base.href = new URL(basis, location.href).href;
    doc.head.insertBefore(base, doc.head.firstChild);
    var huelle = doc.createElement('div');
    huelle.innerHTML = mainHtml;
    doc.querySelector('main').replaceWith(huelle.firstElementChild);
    Array.prototype.forEach.call(doc.querySelectorAll('script'), function (s) { s.remove(); });
    var st = doc.createElement('style');
    st.textContent = 'a{pointer-events:none}' + (zusatzCss || '');
    doc.head.appendChild(st);
    return '<!doctype html>' + doc.documentElement.outerHTML;
  }

  function vorschauBeitrag(d) {
    return holeSeite(BEITRAG_VORLAGE).then(function (vorlage) {
      var held = '<div class="sch-reporthero sp-held sp-kopfbild"><img src="' + eh(bildFuer(d.bild)) + '" alt=""><div><span>' +
        eh(d.rubrik || 'News') + '</span><h1>' + eh(d.titel) + '</h1><p class="sp-datum">' + eh(datumDe(d.datum)) + '</p></div></div>';
      var inhalt = vorschauText(d.text);
      if (d.galerie.length) inhalt += '<div class="sp-galerie">' + d.galerie.map(function (g) { return '<img src="' + eh(rohUrl(g)) + '" alt="">'; }).join('') + '</div>';
      return seiteMit(vorlage, '../seiten/', '<main class="sch-report sp-seite">' + held + '<article class="sp-inhalt">' + inhalt + '</article></main>');
    });
  }

  function vorschauSpielbericht(d) {
    return holeSeite(SB_VORLAGE).then(function (vorlage) {
      var sp = spielFelder();
      var team = form.sp_mannschaft.value || 'm1';
      var opt = form.sp_mannschaft.selectedOptions && form.sp_mannschaft.selectedOptions[0];
      var teamName = opt ? opt.textContent : '';
      var heim = form.sp_ort_art.value !== 'auswaerts';
      var sch = { name: '1. SC 1911 Heiligenstadt' + (team === 'm2' ? ' II' : ''), wappen: 'sch-startseite/assets/logo.png' };
      var geg = { name: sp.gegner || 'Gegner', wappen: wappen ? rohUrl(wappen) : 'assets/wappen/' + wappenSlug(sp.gegner) + '.png' };
      var paar = heim ? [sch, geg] : [geg, sch];
      function stand(a, b) { return heim ? a + ' : ' + b : b + ' : ' + a; }
      var oben = eh(sp.wettbewerb || 'Spiel');
      if (team !== 'm1' && teamName) oben = eh(teamName) + ' · ' + oben;
      var zweite = [sp.runde, sp.spielort].filter(Boolean).map(eh).join(', ');
      var zeit = eh(datumTag(sp.spieldatum || d.datum)) + (sp.anstoss ? ' | ' + eh(sp.anstoss) + ' Uhr' : '');
      var hatEnde = sp.end_sch !== '' && sp.end_geg !== '';
      var tore = (sp.tore_sch || '').split('\n').filter(function (x) { return x.trim(); })
        .map(function (x) { return '<li><span>' + eh(x.trim()) + '</span></li>'; }).join('');
      var weg = ' onerror="this.style.visibility=\'hidden\'"';
      var tafel = '<section class="sb-tafel" aria-label="Ergebnis"><div class="sb-tafel-innen">' +
        '<div class="sb-meta"><span class="sb-meta-icon"></span><p><b>' + oben + '</b>' + zweite + (zweite ? '<br>' : '') + zeit + '</p></div>' +
        '<div class="sb-paar"><span class="sb-team stitel">' + eh(paar[0].name) + '</span><img class="sb-wappen" src="' + eh(paar[0].wappen) + '" alt=""' + weg + '>' +
        '<div class="sb-stand"><strong>' + (hatEnde ? stand(sp.end_sch, sp.end_geg) : '– : –') + '</strong>' +
        (sp.hz_sch !== '' && sp.hz_geg !== '' ? '<span>Halbzeit ' + stand(sp.hz_sch, sp.hz_geg) + '</span>' : '') + '</div>' +
        '<img class="sb-wappen" src="' + eh(paar[1].wappen) + '" alt=""' + weg + '><span class="sb-team stitel">' + eh(paar[1].name) + '</span></div>' +
        '<span class="sb-status">' + (hatEnde ? 'Beendet' : 'Spielbericht') + '</span>' +
        (tore ? '<ul class="sb-tore">' + tore + '</ul>' : '') + '</div></section>';
      // Text in Abschnitte je Zwischenüberschrift, Galeriebilder dazwischen wie auf der fertigen Seite
      var teile = vorschauText(d.text).split(/(?=<h[23]>)/).map(function (t) {
        return t.replace(/<h[23]>/, '<h3 class="stitel">').replace(/<\/h[23]>/, '</h3>');
      });
      var bilder = d.galerie.slice(), artikel = '';
      teile.forEach(function (t, k) {
        artikel += '<section class="sb-weiter">' + t + '</section>';
        if (k % 2 === 1 && bilder.length) artikel += '<figure><img src="' + eh(rohUrl(bilder.shift())) + '" alt=""></figure>';
      });
      bilder.forEach(function (b) { artikel += '<figure><img src="' + eh(rohUrl(b)) + '" alt=""></figure>'; });
      var main = '<main class="sb"><header class="sb-held sb-held-ganz"><img class="sb-held-bild" src="' + eh(bildFuer(d.bild)) + '" alt="">' +
        '<h1 class="stitel">Spielbericht</h1></header>' + tafel +
        '<div class="sb-reiter-band"><div class="sb-reiter" role="tablist"><button type="button" role="tab" aria-selected="true">Spielbericht</button></div></div>' +
        '<section class="sb-bereich"><article class="sb-artikel"><h2 class="stitel">' + eh(d.titel) + '</h2><p class="sb-autor">' +
        eh(datumLang(d.datum)) + '</p>' + artikel + '</article></section></main>';
      return seiteMit(vorlage, '../', main);
    });
  }

  function vorschauKarte(d) {
    return holeSeite(BEITRAG_VORLAGE).then(function (vorlage) {
      var teaser = d.teaser || textfeld.textContent.trim().slice(0, 230);
      var karte = '<a class="sp-karte" href="#"><span class="sp-kartenbild"><img src="' + eh(bildFuer(d.bild)) + '" alt=""></span>' +
        '<span class="sp-kartentext"><time>' + eh(datumDe(d.datum)) + '</time><b>' + eh(d.titel) + '</b><span>' + eh(teaser) +
        '</span><em>Beitrag lesen</em></span></a>';
      return seiteMit(vorlage, '../seiten/', '<main class="sch-report sp-seite"><article class="sp-inhalt" style="padding:24px 16px">' +
        '<div class="sp-karten" style="grid-template-columns:1fr">' + karte + '</div></article></main>',
        '.sp-nav,.sch-footer{display:none!important}body{background:#eef2f7}');
    });
  }

  function zeigeVorschau() {
    normalisiereText();
    var d = { titel: form.titel.value.trim() || 'Ohne Titel', datum: form.datum.value, rubrik: form.rubrik.value,
      teaser: form.teaser.value.trim(), text: textfeld.innerHTML, bild: titelbild, galerie: galerie.slice() };
    var istSb = d.rubrik === 'Spielbericht' && !!form.sp_gegner.value.trim();
    $('[data-vorschauhinweis]').textContent = vorschauAnsicht === 'karte' ? 'So erscheint der Beitrag in der Liste unter News und auf der Startseite.' :
      istSb ? 'Spielbericht: Kopf, Ergebnistafel und Text. Die übrigen Reiter (Aufstellung, Statistik …) gibt es erst auf der fertigen Seite.' :
      d.rubrik === 'Spielbericht' ? 'Für die Ergebnistafel bei den Spieldaten den Gegner eintragen.' : '';
    $('[data-vorschaubuehne]').className = 'vorschau-buehne ' + vorschauAnsicht;
    var p = vorschauAnsicht === 'karte' ? vorschauKarte(d) : istSb ? vorschauSpielbericht(d) : vorschauBeitrag(d);
    return p.then(function (html) { vorschauRahmen.srcdoc = html; }, function (e) {
      vorschauRahmen.srcdoc = '<p style="font:16px Arial;padding:24px">Vorschau nicht möglich: ' + eh(e.message) + '</p>';
    });
  }
  $('[data-vorschau]').addEventListener('click', function () {
    vorschauDialog.showModal();
    zeigeVorschau();
  });
  $$('[data-vansicht]').forEach(function (b) {
    b.addEventListener('click', function () {
      vorschauAnsicht = b.dataset.vansicht;
      $$('[data-vansicht]').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      zeigeVorschau();
    });
  });
  $('[data-vorschauzu]').addEventListener('click', function () { vorschauDialog.close(); });
  vorschauDialog.addEventListener('click', function (e) { if (e.target === vorschauDialog) vorschauDialog.close(); });
})();
