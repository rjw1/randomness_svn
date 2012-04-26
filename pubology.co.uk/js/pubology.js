$(
  function() {
    $('#upload_msg').text('Uploading... please be patient, this may take '
                          + 'a little while.');
    $('#upload_msg').hide();

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
  }
);

function reassure() {
  $('#upload_msg').show();
  return true;
}
