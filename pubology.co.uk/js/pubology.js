$(
  function() {
    $('#upload_msg').text('Uploading... please be patient, this may take '
                          + 'a little while.');
    $('#upload_msg').hide();

    $('#navbar').portamento();
    var main_height = $('#main_content').height();
    var nav_height = $('#navbar_wrapper').height();
    if ( nav_height < main_height ) {
      $('#navbar_wrapper').height( main_height );
    }
  }
);

function reassure() {
  $('#upload_msg').show();
  return true;
}
