<?php
/**
 * Plugin Name: SC 1911 Startseite
 * Description: Die neue Startseite des 1. SC 1911 Heiligenstadt. News kommen live aus WordPress, Ergebnisse und Spiele von FuPa (vom Server abgefragt, Besucher laden nichts bei FuPa). Nach dem Aktivieren sehen nur angemeldete Redakteure die neue Seite unter ?sch-neu=1; für alle Besucher schaltet man sie unter Einstellungen → SC Startseite ein. Zum Abschalten einfach deaktivieren, die alte Startseite ist dann sofort wieder da. Gebaut aus dem Repo sch-website (wordpress-plugin/baue-plugin.py) – Änderungen dort, nicht hier.
 * Version: 1.0
 * Author: 1. SC 1911 e.V. Heilbad Heiligenstadt
 * Requires PHP: 7.0
 * Requires at least: 5.6
 */

// Direktaufruf der Datei abweisen.
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

define( 'SC1911_SP_DIR', plugin_dir_path( __FILE__ ) );
define( 'SC1911_SP_WEB', plugins_url( 'web/', __FILE__ ) );
define( 'SC1911_SP_OPTION', 'sc1911_startseite_live' );

require_once SC1911_SP_DIR . 'daten.php';

/**
 * Soll die neue Startseite für diesen Aufruf erscheinen?
 * Live: für alle auf der Startseite. Sonst nur Redakteure mit ?sch-neu=1.
 */
function sc1911_sp_aktiv() {
	if ( ! is_front_page() || is_admin() || is_feed() ) {
		return false;
	}
	if ( get_option( SC1911_SP_OPTION ) ) {
		return true;
	}
	return isset( $_GET['sch-neu'] ) && current_user_can( 'edit_posts' );
}

function sc1911_sp_vorschau() {
	return ! get_option( SC1911_SP_OPTION );
}

// Eigene Vorlage statt der des Themes.
add_filter( 'template_include', function ( $vorlage ) {
	return sc1911_sp_aktiv() ? SC1911_SP_DIR . 'vorlage.php' : $vorlage;
}, 99 );

/**
 * Styles und Skripte der Startseite laden, die des Themes (Enfold) weglassen.
 * Andere Plugins (z. B. der Cookie-Banner) laufen über wp_head/wp_footer weiter.
 */
add_action( 'wp_enqueue_scripts', function () {
	if ( ! sc1911_sp_aktiv() ) {
		return;
	}
	$theme = array( get_template_directory_uri(), get_stylesheet_directory_uri() );
	foreach ( array( wp_styles(), wp_scripts() ) as $liste ) {
		foreach ( $liste->queue as $name ) {
			$src = isset( $liste->registered[ $name ] ) ? (string) $liste->registered[ $name ]->src : '';
			foreach ( $theme as $t ) {
				if ( $src !== '' && strpos( $src, $t ) === 0 ) {
					wp_dequeue_style( $name );
					wp_dequeue_script( $name );
				}
			}
		}
	}
	foreach ( sc1911_sp_dateien( 'css' ) as $i => $datei ) {
		wp_enqueue_style( 'sc1911-sp-' . $i, SC1911_SP_WEB . $datei, array(), sc1911_sp_stand( $datei ) );
	}
	foreach ( sc1911_sp_dateien( 'js' ) as $i => $datei ) {
		wp_enqueue_script( 'sc1911-sp-' . $i, SC1911_SP_WEB . $datei, array(), sc1911_sp_stand( $datei ), true );
	}
}, 999 );

// Reihenfolge wie auf der Vorlage (index.html); geschrieben von baue-plugin.py.
function sc1911_sp_dateien( $art ) {
	$liste = json_decode( (string) file_get_contents( SC1911_SP_DIR . 'web/dateien.json' ), true );
	return isset( $liste[ $art ] ) ? $liste[ $art ] : array();
}

// Änderungsdatum als Version: nach einem Plugin-Update lädt jeder Browser neu.
function sc1911_sp_stand( $datei ) {
	$pfad = SC1911_SP_DIR . 'web/' . $datei;
	return file_exists( $pfad ) ? (string) filemtime( $pfad ) : '1.0';
}

// Hinweis oben auf der Seite, solange nur die Vorschau läuft.
add_action( 'wp_footer', function () {
	if ( ! sc1911_sp_aktiv() || ! sc1911_sp_vorschau() ) {
		return;
	}
	echo '<div class="sch-wp-vorschau" role="status">Vorschau – Besucher sehen noch die alte Startseite. <a href="' . esc_url( admin_url( 'options-general.php?page=sc1911-startseite' ) ) . '">Einstellungen</a></div>';
} );

// ---------- Einstellungen → SC Startseite ----------

add_action( 'admin_init', function () {
	register_setting( 'sc1911_startseite', SC1911_SP_OPTION, array(
		'type'              => 'boolean',
		'sanitize_callback' => function ( $wert ) {
			return $wert ? 1 : 0;
		},
		'default'           => 0,
	) );
	// Spiele sofort neu von FuPa holen.
	if ( isset( $_POST['sc1911_sp_neu_laden'] ) && current_user_can( 'manage_options' ) && check_admin_referer( 'sc1911_sp_neu_laden' ) ) {
		delete_transient( 'sc1911_sp_fupa' );
		sc1911_sp_fupa_spiele();
		add_settings_error( 'sc1911_startseite', 'neu', 'Spiele wurden neu von FuPa geholt.', 'updated' );
	}
} );

add_action( 'admin_menu', function () {
	add_options_page( 'SC Startseite', 'SC Startseite', 'manage_options', 'sc1911-startseite', 'sc1911_sp_einstellungen' );
} );

function sc1911_sp_einstellungen() {
	$letzt = get_option( 'sc1911_sp_fupa_letzt' );
	?>
	<div class="wrap">
		<h1>SC Startseite</h1>
		<?php settings_errors( 'sc1911_startseite' ); ?>
		<p>Die neue Startseite zeigt die News aus WordPress und die Spiele von FuPa. Solange sie nicht eingeschaltet ist, sehen Besucher die bisherige Startseite.</p>
		<p><a class="button" href="<?php echo esc_url( add_query_arg( 'sch-neu', '1', home_url( '/' ) ) ); ?>" target="_blank" rel="noopener">Vorschau ansehen</a></p>
		<form method="post" action="options.php">
			<?php settings_fields( 'sc1911_startseite' ); ?>
			<label><input type="checkbox" name="<?php echo esc_attr( SC1911_SP_OPTION ); ?>" value="1" <?php checked( get_option( SC1911_SP_OPTION ) ); ?>> Neue Startseite für alle Besucher einschalten</label>
			<p class="description">Arbeitet die Seite mit einem Cache-Plugin, danach dort den Cache leeren.</p>
			<?php submit_button( 'Speichern' ); ?>
		</form>
		<h2>Spiele von FuPa</h2>
		<p><?php echo $letzt && ! empty( $letzt['zeit'] ) ? 'Zuletzt geholt: ' . esc_html( wp_date( 'd.m.Y H:i', (int) $letzt['zeit'] ) ) . ' Uhr. Die Seite holt sie alle 30 Minuten selbst.' : 'Noch nicht geholt.'; ?></p>
		<form method="post">
			<?php wp_nonce_field( 'sc1911_sp_neu_laden' ); ?>
			<?php submit_button( 'Jetzt neu holen', 'secondary', 'sc1911_sp_neu_laden', false ); ?>
		</form>
	</div>
	<?php
}

// Link „Einstellungen“ in der Plugin-Liste.
add_filter( 'plugin_action_links_' . plugin_basename( __FILE__ ), function ( $links ) {
	array_unshift( $links, '<a href="' . esc_url( admin_url( 'options-general.php?page=sc1911-startseite' ) ) . '">Einstellungen</a>' );
	return $links;
} );
