$(
  function() {

    $('input.checkbox').each( function( index ) {
      set_checkbox_colour( $(this) );
    } );

    $('input.checkbox').click( function() {
      set_checkbox_colour( $(this) );
    } );

    $('td.checklist_address').click( function() {
      var elem = $(this).siblings('td.checklist_status')
                        .children('input.checkbox');
      if ( elem.is(':checked') ) {
        elem.removeAttr( 'checked' );
      } else {
        elem.attr( 'checked', 'checked' );
      }
      set_checkbox_colour( elem );
    } );

  }
);

function set_checkbox_colour( elem ) {
  var colour;
  if ( elem.is(':checked') ) {
    colour = '#00ff00';
  } else {
    colour = 'white';
  }
  elem.parent().css( 'background-color', colour );
  elem.parent().siblings('td.checklist_address')
               .css( 'background-color', colour );
}
