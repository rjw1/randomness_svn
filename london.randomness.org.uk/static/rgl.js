var node_param, map_links;

$(
  function() {
    // Click to reveal the map links.
    map_links = $( '.map_links' ).html();
    if ( !/^\s*$/.test( map_links ) ) {
      hide_map_links();
    }

    // Nearby Tube stuff.
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

var show_button = '(<a href="#" id="show_map_links">show map links</a>)';
var hide_button = '(<a href="#" id="hide_map_links">hide map links</a>)';

function hide_map_links() {
  $( '.map_links' ).html( show_button );
  $( '#show_map_links' ).click(
    function() {
      show_map_links();
      return false;
    }
  );
}

function show_map_links() {
  $( '.map_links' ).html( map_links + hide_button );
  $( '#hide_map_links' ).click(
    function() {
      hide_map_links();
      return false;
    }
  );
}
