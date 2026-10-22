<?php
/**
 * Die beweglichen Teile der Startseite: News aus WordPress, Spiele von FuPa.
 * Das Markup ist dasselbe wie in index.html (sch-website), damit die CSS passt.
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

// ---------- News ----------

// "+++ Serie hält weiter +++" -> "Serie hält weiter"
function sc1911_sp_titel( $post ) {
	$t = html_entity_decode( wp_strip_all_tags( get_the_title( $post ) ), ENT_QUOTES, 'UTF-8' );
	return trim( preg_replace( '/^[\s+]+|[\s+]+$/u', '', $t ) );
}

function sc1911_sp_auszug( $post, $laenge ) {
	$text = has_excerpt( $post ) ? $post->post_excerpt : $post->post_content;
	$text = strip_shortcodes( $text );
	$text = preg_replace( '/\[\/?[a-z_]+[^\]]*\]/i', ' ', $text ); // Enfold-Shortcodes, auch ohne Theme
	$text = html_entity_decode( wp_strip_all_tags( $text ), ENT_QUOTES, 'UTF-8' );
	$text = trim( preg_replace( '/\s+/u', ' ', $text ) );
	$text = preg_replace( '/\s*(Weiterlesen|\[…\]|…)\s*$/u', '', $text );
	if ( mb_strlen( $text ) > $laenge ) {
		$text = mb_substr( $text, 0, $laenge );
		$text = preg_replace( '/\s+\S*$/u', '', $text ) . ' …';
	}
	return $text;
}

function sc1911_sp_beitraege( $anzahl, $versatz ) {
	return get_posts( array(
		'numberposts'         => $anzahl,
		'offset'              => $versatz,
		'post_type'           => 'post',
		'post_status'         => 'publish',
		'ignore_sticky_posts' => true,
		'suppress_filters'    => false,
	) );
}

function sc1911_sp_bild( $post ) {
	$url = get_the_post_thumbnail_url( $post, 'large' );
	return $url ? $url : SC1911_SP_WEB . 'assets/hero.jpg';
}

// Die drei neuesten Beiträge (Block unter dem Titelbild).
function sc1911_sp_neueste() {
	foreach ( sc1911_sp_beitraege( 3, 0 ) as $p ) {
		printf(
			'<a class="sch-post" href="%s"><div class="sch-postimage"><img src="%s" alt="" loading="lazy" width="840" height="316"></div><div class="sch-postcopy"><time datetime="%s">%s</time><h2>%s</h2><p class="sch-excerpt">%s</p><span class="sch-read">Beitrag lesen</span></div></a>',
			esc_url( get_permalink( $p ) ),
			esc_url( sc1911_sp_bild( $p ) ),
			esc_attr( get_the_date( 'c', $p ) ),
			esc_html( get_the_date( 'd.m.Y', $p ) ),
			esc_html( sc1911_sp_titel( $p ) ),
			esc_html( sc1911_sp_auszug( $p, 330 ) )
		);
	}
}

// Die nächsten acht ("Was läuft weiter beim SCH?").
function sc1911_sp_weitere() {
	foreach ( sc1911_sp_beitraege( 8, 3 ) as $p ) {
		printf(
			'<a class="sch-morecard" href="%s"><div class="sch-moreimage"><img src="%s" alt="" loading="lazy" width="840" height="316"></div><div class="sch-morecopy"><time datetime="%s">%s</time><h3>%s</h3><p>%s</p><span>Beitrag lesen</span></div></a>',
			esc_url( get_permalink( $p ) ),
			esc_url( sc1911_sp_bild( $p ) ),
			esc_attr( get_the_date( 'c', $p ) ),
			esc_html( get_the_date( 'd.m.Y', $p ) ),
			esc_html( sc1911_sp_titel( $p ) ),
			esc_html( sc1911_sp_auszug( $p, 200 ) )
		);
	}
}

// ---------- Spiele (FuPa) ----------

define( 'SC1911_SP_VEREIN', '1-sc-1911-heiligenstadt' );

/**
 * Alle Spiele des Vereins ab 45 Tagen vor heute. 30 Minuten zwischengespeichert;
 * fällt FuPa aus, bleibt der letzte gute Stand stehen.
 */
function sc1911_sp_fupa_spiele() {
	$spiele = get_transient( 'sc1911_sp_fupa' );
	if ( is_array( $spiele ) ) {
		return $spiele;
	}
	$url  = 'https://api.fupa.net/v1/clubs/' . SC1911_SP_VEREIN . '/seasons/current/matches?from=' . gmdate( 'Y-m-d', time() - 45 * DAY_IN_SECONDS ) . '&limit=100';
	$antw = wp_remote_get( $url, array( 'timeout' => 8, 'user-agent' => 'SC1911-Startseite/1.0 (' . home_url() . ')' ) );
	$daten = is_wp_error( $antw ) || wp_remote_retrieve_response_code( $antw ) !== 200 ? null : json_decode( wp_remote_retrieve_body( $antw ), true );
	if ( is_array( $daten ) && isset( $daten[0]['kickoff'] ) ) {
		$spiele = sc1911_sp_fupa_kurz( $daten );
		update_option( 'sc1911_sp_fupa_letzt', array( 'zeit' => time(), 'spiele' => $spiele ), false );
		set_transient( 'sc1911_sp_fupa', $spiele, 30 * MINUTE_IN_SECONDS );
		return $spiele;
	}
	// Fehler: letzten guten Stand nehmen und erst in 5 Minuten wieder fragen.
	$letzt  = get_option( 'sc1911_sp_fupa_letzt' );
	$spiele = $letzt && isset( $letzt['spiele'] ) ? $letzt['spiele'] : array();
	set_transient( 'sc1911_sp_fupa', $spiele, 5 * MINUTE_IN_SECONDS );
	return $spiele;
}

// Nur die Felder behalten, die die Karten brauchen.
function sc1911_sp_fupa_kurz( $daten ) {
	$aus = array();
	foreach ( $daten as $m ) {
		if ( empty( $m['homeTeam'] ) || empty( $m['awayTeam'] ) || empty( $m['kickoff'] ) ) {
			continue;
		}
		if ( ! empty( $m['flags'] ) && in_array( 'aborted', (array) $m['flags'], true ) ) {
			continue;
		}
		$heim = isset( $m['homeTeam']['clubSlug'] ) && $m['homeTeam']['clubSlug'] === SC1911_SP_VEREIN;
		$wir  = $heim ? $m['homeTeam'] : $m['awayTeam'];
		$die  = $heim ? $m['awayTeam'] : $m['homeTeam'];
		$team = str_replace( array( SC1911_SP_VEREIN . '-', '-' ), array( '', '' ), preg_replace( '/-\d{4}-\d{2}$/', '', (string) $wir['slug'] ) );
		$aus[] = array(
			'team'     => $team, // m1, m2, u17-1 -> u171 ...
			'heim'     => $heim,
			'gegner'   => isset( $die['name']['full'] ) ? (string) $die['name']['full'] : '',
			'anstoss'  => (string) $m['kickoff'],
			'fertig'   => isset( $m['section'] ) && $m['section'] === 'POST' && isset( $m['homeGoal'] ) && $m['homeGoal'] !== null,
			'tore'     => array( isset( $m['homeGoal'] ) ? (int) $m['homeGoal'] : 0, isset( $m['awayGoal'] ) ? (int) $m['awayGoal'] : 0 ),
			'wettb'    => isset( $m['competition']['name'] ) ? (string) $m['competition']['name'] : '',
			'slug'     => (string) $m['slug'],
		);
	}
	usort( $aus, function ( $a, $b ) {
		return strcmp( $a['anstoss'], $b['anstoss'] );
	} );
	return $aus;
}

function sc1911_sp_wettbewerb( $n ) {
	if ( strpos( $n, 'Landespokal' ) !== false ) {
		return 'Thüringenpokal';
	}
	if ( strpos( $n, 'Kreispokal' ) !== false ) {
		return 'Kreispokal';
	}
	foreach ( array( 'Verbandsliga', 'Talenteliga', 'Landesklasse', 'Kreisoberliga', 'Kreisliga', 'Kreisklasse' ) as $w ) {
		if ( strpos( $n, $w ) !== false ) {
			return $w;
		}
	}
	return 'Freundschaftsspiel';
}

// Kürzel im Kreis; feste für die häufigen Gegner, sonst aus dem Namen.
function sc1911_sp_kuerzel( $name ) {
	$fest = array(
		'FSV 1996 Preußen Bad Langensalza' => 'PBL', '1. FC Eichsfeld' => 'FCE', 'TSV Gera-Westvororte' => 'GWV',
		'FSV Schleiz' => 'FSV', 'FSV Wacker Nordhausen' => 'W90', 'SV Gernrode 1887' => 'GERN',
		'SG Leinefelde / SG Birkungen' => 'LEI', 'Bad Tennstedt' => 'TEN', 'FC Union Mühlhausen' => 'FCU',
		'BSV Blau Weiß 22 Lengenfeld/Stein' => 'LEN', 'JFC Gera' => 'JFC', 'SV DJK Arenshausen' => 'ARE',
		'SG SV Rot-Weiß Buttlar' => 'BUT', 'SV Blau-Weiß Brehme' => 'BRE', 'FC Rot-Weiß Erfurt U16' => 'RWE',
		'FC Rot-Weiß Erfurt' => 'RWE', '1. Suhler SV' => 'SUH', 'SpVgg Geratal' => 'GER',
		'SG SV Schwarz-Rot Wingerode' => 'WIN',
	);
	if ( isset( $fest[ $name ] ) ) {
		return $fest[ $name ];
	}
	$vorsilben = array( 'sg', 'sv', 'fc', 'fsv', 'tsv', 'djk', 'jfv', 'spvgg', 'ssv', 'jfc', 'sc', 'fv', 'vfb', 'vfl', 'tsg', 'bsv', 'esv', 'u15', 'u16', 'u17', 'u19' );
	$worte     = array();
	foreach ( preg_split( '/[\s\/]+/u', $name ) as $w ) {
		if ( $w !== '' && ! in_array( mb_strtolower( trim( $w, '.' ) ), $vorsilben, true ) && ! preg_match( '/^[\d.]+$/', $w ) ) {
			$worte[] = $w;
		}
	}
	if ( ! $worte ) {
		return mb_strtoupper( mb_substr( $name, 0, 3 ) );
	}
	$w = $worte[0];
	if ( strpos( $w, '-' ) !== false ) {
		$k = '';
		foreach ( explode( '-', $w ) as $teil ) {
			$k .= $teil !== '' ? mb_substr( $teil, 0, 1 ) : '';
		}
		if ( isset( $worte[1] ) ) {
			$k .= mb_substr( $worte[1], 0, 1 );
		}
		$k = mb_strtoupper( mb_substr( $k, 0, 4 ) );
	} else {
		$k = mb_strtoupper( mb_substr( $w, 0, 3 ) );
	}
	return $k === 'SCH' ? 'GEG' : $k;
}

// Jugendteams auf FuPa -> Name auf der Seite.
function sc1911_sp_jugend() {
	return array( 'u191' => 'U19', 'u171' => 'U17', 'u172' => 'U16', 'u151' => 'U15', 'u131' => 'U13', 'u122' => 'U12', 'u133' => 'U13 III', 'u111' => 'U11', 'u112' => 'U11 II' );
}

/**
 * Spielbericht zu einem Spiel: der erste Beitrag zwischen 100 Minuten und
 * 20 Stunden nach Anpfiff, der keine Vorschau ist (MATCHDAY, Wochenendübersicht).
 */
function sc1911_sp_bericht( $sp, &$benutzt ) {
	$start = strtotime( $sp['anstoss'] );
	if ( ! $start ) {
		return '';
	}
	$posts = get_posts( array(
		'numberposts' => 5,
		'post_status' => 'publish',
		'orderby'     => 'date',
		'order'       => 'ASC',
		'date_query'  => array( array(
			'after'     => wp_date( 'Y-m-d H:i:s', $start + 100 * MINUTE_IN_SECONDS ),
			'before'    => wp_date( 'Y-m-d H:i:s', $start + 20 * HOUR_IN_SECONDS ),
			'inclusive' => true,
		) ),
	) );
	foreach ( $posts as $p ) {
		if ( in_array( $p->ID, $benutzt, true ) || preg_match( '/matchday|alle unsere spiele|parksituation|vorbericht|anpfiff/i', $p->post_title ) ) {
			continue;
		}
		$benutzt[] = $p->ID;
		return get_permalink( $p );
	}
	return '';
}

function sc1911_sp_karte( $sp, $jugend, $bericht ) {
	$jg     = sc1911_sp_jugend();
	$nr     = substr( $sp['team'], -1 );
	$zusatz = $nr === '2' ? ' II' : ( $nr === '3' ? ' III' : '' );
	$logo   = esc_url( SC1911_SP_WEB . 'assets/logo.png' );
	$unser  = '<span class="sch-matchteam"><img src="' . $logo . '" alt="" width="827" height="945"><b>SCH</b><span class="sch-teamname">1. SC Heiligenstadt' . $zusatz . '</span></span>';
	$k      = esc_html( sc1911_sp_kuerzel( $sp['gegner'] ) );
	$gegner = '<span class="sch-matchteam"><span class="sch-teammark" aria-hidden="true">' . $k . '</span><b>' . $k . '</b><span class="sch-teamname">' . esc_html( $sp['gegner'] ) . '</span></span>';
	$links  = $sp['heim'] ? $unser : $gegner;
	$rechts = $sp['heim'] ? $gegner : $unser;
	$wb     = sc1911_sp_wettbewerb( $sp['wettb'] );
	$meta   = $jugend ? ( isset( $jg[ $sp['team'] ] ) ? $jg[ $sp['team'] ] : strtoupper( $sp['team'] ) ) . ' · ' . $wb : $wb;
	$a      = $sp['anstoss'];
	$zeit   = substr( $a, 8, 2 ) . '.' . substr( $a, 5, 2 ) . '.' . substr( $a, 0, 4 ) . ' | ' . substr( $a, 11, 5 ) . ' Uhr';
	$ziel   = $bericht ? $bericht : 'https://www.fupa.net/match/' . rawurlencode( $sp['slug'] );
	$kopf   = '<span class="sch-matchmeta">' . esc_html( $meta ) . '</span><time datetime="' . esc_attr( $a ) . '">' . esc_html( $zeit ) . '</time>';
	if ( $sp['fertig'] ) {
		list( $h, $g ) = $sp['tore'];
		$uns = $sp['heim'] ? $h : $g;
		$ihr = $sp['heim'] ? $g : $h;
		$art = $uns > $ihr ? array( 'win', 'Sieg' ) : ( $uns < $ihr ? array( 'loss', 'Niederlage' ) : array( 'draw', 'Unentschieden' ) );
		return '<a class="sch-game sch-finished sch-' . $art[0] . '" href="' . esc_url( $ziel ) . '"><span class="sch-outcome">' . $art[1] . '</span>' . $kopf
			. '<span class="sch-gamepair">' . $links . '<strong class="sch-result">' . $h . ' : ' . $g . '</strong>' . $rechts . '</span>'
			. '<span class="sch-matchlink">' . ( $bericht ? 'Zum Spielbericht' : 'Zur Spielübersicht' ) . ' <span aria-hidden="true">→</span></span></a>';
	}
	return '<a class="sch-game sch-upcoming" href="' . esc_url( $ziel ) . '">' . $kopf
		. '<span class="sch-gamepair">' . $links . '<strong class="sch-result">–</strong>' . $rechts . '</span>'
		. '<span class="sch-matchlink">Zum Spiel <span aria-hidden="true">→</span></span></a>';
}

/**
 * Eine Spur mit Karten: die letzten Ergebnisse, dann die nächsten Spiele.
 * $reihe: men (1. Mannschaft), reserve (2. Mannschaft), youth (Nachwuchs).
 */
function sc1911_sp_spiele( $reihe ) {
	static $benutzt = array();
	$jugend = $reihe === 'youth';
	$alt    = $jugend ? 5 : 3;
	$neu    = $jugend ? 5 : 3;
	$jg     = sc1911_sp_jugend();
	$fertig = array();
	$kommt  = array();
	foreach ( sc1911_sp_fupa_spiele() as $sp ) {
		$passt = $jugend ? isset( $jg[ $sp['team'] ] ) : $sp['team'] === ( $reihe === 'men' ? 'm1' : 'm2' );
		if ( ! $passt ) {
			continue;
		}
		if ( $sp['fertig'] ) {
			$fertig[] = $sp;
		} elseif ( strtotime( $sp['anstoss'] ) > time() - 3 * HOUR_IN_SECONDS ) {
			$kommt[] = $sp;
		}
	}
	$fertig = array_slice( $fertig, -$alt );
	$kommt  = array_slice( $kommt, 0, $neu );
	$karten = '';
	foreach ( $fertig as $sp ) {
		$karten .= sc1911_sp_karte( $sp, $jugend, $jugend ? '' : sc1911_sp_bericht( $sp, $benutzt ) );
	}
	foreach ( $kommt as $sp ) {
		$karten .= sc1911_sp_karte( $sp, $jugend, '' );
	}
	if ( $karten === '' ) {
		$karten = '<p class="sch-matchsource">Die Spiele sind gerade nicht abrufbar.</p>';
	}
	echo '<div class="sch-gametrack" data-initial="' . max( 0, count( $fertig ) - 1 ) . '">' . $karten . '</div>'; // Karten sind oben escaped
}

function sc1911_sp_standzeile() {
	$letzt = get_option( 'sc1911_sp_fupa_letzt' );
	$zeit  = $letzt && ! empty( $letzt['zeit'] ) ? wp_date( 'd.m.Y H:i', (int) $letzt['zeit'] ) . ' Uhr' : '–';
	echo '<p class="sch-matchsource">Stand: ' . esc_html( $zeit ) . ' · Ergebnisse: FUPA · Terminänderungen möglich.</p>';
}
