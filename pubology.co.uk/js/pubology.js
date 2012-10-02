var sources_text;

$(
  function() {
    $('#upload_msg').text('Uploading... please be patient, this may take '
                          + 'a little while.');
    $('#upload_msg').hide();

    // Banner.
    $('#banner h1 a').html( '&nbsp;' );
    $('#banner').anystretch( '/images/banner.jpg' );
    $('#banner h1 a').height(75);

    // Navbar that scrolls with the page.
    $('#navbar').portamento();

    // Make the navbar colour go all the way down.
    var main_height = $('#main_content').height();
    var nav_height = $('#navbar_wrapper').height();
    var banner = $('#banner');
    var banner_pad = banner.innerHeight() - banner.height();
    var win_height = $(window).height() - banner.height()
                     + ( banner_pad / 2 ) - 1;
    if ( nav_height < main_height ) {
      $('#navbar_wrapper').height( main_height );
      nav_height = main_height; // so next check works
    }

    if ( nav_height < win_height ) {
      $('#navbar_wrapper').height( win_height );
    }

    // Hide the sources and references by default.
    sources_text = $( '#pub_sources_and_references' ).html();
    hide_sources();
  }
);

function reassure() {
  $('#upload_msg').show();
  return true;
}

var show_button = '(<a href="#" id="show_sources">show sources and references</a>)';
var hide_button = '(<a href="#" id="hide_sources">hide sources and references</a>)';

function hide_sources() {
  $( '#pub_sources_and_references' ).html( show_button );
  $( '#show_sources' ).click(
    function() {
      show_sources();
      return false;
    }
  );
}

function show_sources() {
  $( '#pub_sources_and_references' ).html( sources_text + hide_button );
  $( '#hide_sources' ).click(
    function() {
      hide_sources();
      return false;
    }
  );
}
