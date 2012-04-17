var tubeReq;
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
        if (window.XMLHttpRequest) {
          tubeReq = new XMLHttpRequest();
          tubeReq.onreadystatechange = processTubeReqChange;
          tubeReq.open("GET", url, true);
          tubeReq.send(null);
        } else if (window.ActiveXObject) {
          tubeReq = new ActiveXObject("Microsoft.XMLHTTP");
          if (tubeReq) {
              tubeReq.onreadystatechange = processTubeReqChange;
              tubeReq.open("GET", url, true);
              tubeReq.send();
          }
        }
      }
    );
  }
);

function processTubeReqChange() {
  if (tubeReq.readyState == 4) {
    var results;
    if (tubeReq.status == 200) {
      results = tubeReq.responseText;
    } else {
      results = "Error retrieving data: " + tubeReq.statusText;
    }
    $( '#nearby_tubes' ).Loadingdotdotdot( "Stop" );
    $( '#nearby_tube_results' ).css( { 'padding-left': '0.5em',
                                       'padding-bottom': '0.5em' } );
    $( '#nearby_tube_results' ).html( results );
  }
}
