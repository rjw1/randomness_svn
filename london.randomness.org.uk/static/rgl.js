var node_param;

$(
  function() {
    $( '#nearby_tubes' ).css( { height: '2.5em' } );
    $( '#nearby_tube_results' ).css( { 'padding-left': '0.5em' } );
    $( '#nearby_tube_text' ).text( 'Nearby Tube stations: ' );
    $( '#nearby_tube_results' ).html( '<input type="button" value="Show" class="form_button" id="show_nearby_tubes" />' );

    $( '#show_nearby_tubes' ).click(
      function() {
        $( '#nearby_tube_results' ).css( { 'padding-left': '0' } );
        $( '#nearby_tube_results' ).Loadingdotdotdot(
              { speed: 150, maxDots: 3, word: 'Retrieving data' } );
        // node_param is already URI-encoded
        var url='scripts/nearest-tube.cgi?origin=' + node_param;
        $.ajax( {
          type: 'GET',
          url: url,
          success: function( data ) {
            $( '#nearby_tubes' ).Loadingdotdotdot( "Stop" );
            $( '#nearby_tube_results' ).css( { 'padding-left': '0.5em',
                                               'padding-bottom': '0.5em' } );
            $( '#nearby_tube_results' ).html( data );
          },
          error: function( jqXHR, textStatus, errorThrown ) {
            $( '#nearby_tubes' ).Loadingdotdotdot( "Stop" );
            $( '#nearby_tube_results' ).css( { 'padding-left': '0.5em',
                                               'padding-bottom': '0.5em' } );
            $( '#nearby_tube_results' ).html( 'Sorry! There was an error: '
                                              + errorThrown );
          },
        } );
      }
    );
  }
);
