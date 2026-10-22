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
        linkDialog.showModal();
        return;
      }
      if (befehl === 'formatBlock') {
        // Ein zweiter Klick auf Überschrift/Zitat macht wieder einen Absatz daraus
        var aktuellerBlock = document.queryCommandValue('formatBlock').toLowerCase();
        document.execCommand('formatBlock', false, aktuellerBlock === b.dataset.wert ? 'p' : b.dataset.wert);
        return;
      }
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
