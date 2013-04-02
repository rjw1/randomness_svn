var centre_lat, centre_long, map_type;
var positions = [], markers = [];
var base_url = "http://pubology.co.uk/";
var icons = {};

var gicon = L.Icon.extend( {
    shadowUrl: null,
    iconSize: new L.Point( 32, 32 ),
    iconAnchor: new L.Point( 15, 32 ),
    popupAnchor: new L.Point( 0, -29 )
} );
var icon_base_url = 'http://maps.google.com/mapfiles/ms/micons/';

icons.open = new gicon( icon_base_url + 'green-dot.png' );
icons.closed = new gicon( icon_base_url + 'yellow-dot.png' );
icons.demolished = new gicon( icon_base_url + 'red-dot.png' );

$(
  function() {
    $('#map_canvas').height( $(window).height() - $('#banner').height() );
    map = new L.Map( 'map_canvas' );
    var map_centre = new L.LatLng( centre_lat, centre_long );
    var tile_layer;

    var mq_url = 'http://{s}.mqcdn.com/tiles/1.0.0/osm/{z}/{x}/{y}.png';
    var subdomains = [ 'otile1', 'otile2', 'otile3', 'otile4' ];
    var attrib = 'Data, imagery and map information provided by <a href="http://open.mapquest.co.uk" target="_blank">MapQuest</a>, <a href="http://www.openstreetmap.org/" target="_blank">OpenStreetMap</a> and contributors, <a href="http://creativecommons.org/licenses/by-sa/2.0/" target="_blank">CC-BY-SA</a>';

    tile_layer = new L.TileLayer( mq_url, { maxZoom: 18, attribution: attrib, subdomains: subdomains } );

    var zoom = 13;
    if ( map_type && map_type == 'brewery' ) {
      zoom = 10;
    }
    map.setView( map_centre, zoom ).addLayer( tile_layer );

    add_markers();
  }
);

function add_marker( i, thing, type ) {
  var content, icon, marker, position;

  if ( thing.not_on_map ) {
    return;
  }

  position = new L.LatLng( thing.lat, thing.long );

  if ( thing.demolished ) {
    icon = icons.demolished;
  } else if ( thing.closed ) {
    icon = icons.closed;
  } else {
    icon = icons.open;
  }

  marker = new L.Marker( position, { icon: icon } );
  map.addLayer( marker );

  if ( type && type == 'brewery' ) {
    content = '<b>' + thing.name + '</b>';
  } else {
    content = '<a href="' + base_url + 'pubs/' + thing.id + '.html">' +
              thing.name + '</a>';
  }
  if ( thing.demolished ) {
    content = content + ' (demolished)';
  } else if ( thing.closed ) {
    content = content + ' (closed)';
  }
  content = content + '<br>' + thing.address;
  if ( type && type == 'brewery' ) {
    content = content +
      ( thing.location_accurate ? '' : ' (location on map is approximate)' ) +
      ( thing.dates_open ? '<br><b>Active:</b> ' + thing.dates_open : '' ) +
      ( thing.dates_building ? '<br><b>Opened/closed:</b> ' +
                               thing.dates_building : '' ) +
      ( thing.former_names ? '<br><b>Former name(s)</b>: ' +
                             thing.former_names :'') +
      ( thing.former_address ? '<br><b>Former address(s)</b>: ' +
                               thing.former_address : '' ) +
      ( thing.notes ? '<br><b>Notes:</b> ' + thing.notes : '' ) +
      ( thing.sources ? '<br><b>Sources:</b> ' + thing.sources : '' );
    if ( thing.has_links ) {
      var links = [];
      if ( thing.flickr ) {
        links.push( '<a href="' + thing.flickr + '">Photo</a>' );
      }
      if ( thing.website ) {
        links.push( '<a href="' + thing.website + '">Website</a>' );
      }
      if ( thing.twitter ) {
        links.push( '<a href="https://twitter.com/' + thing.twitter +
                    '">Twitter</a>' );
      }
      if ( thing.rgl ) {
        links.push( '<a href="' + thing.rgl + '">RGL</a>' );
      }
      if ( thing.quaffale ) {
        links.push( '<a href="' + thing.quaffale + '">Quaffale</a>' );
      }
      content = content + '<br><b>Links: </b>' + links.join( ', ' );
    }
  }

  marker.bindPopup( content );

  markers[ i ] = marker;
  positions[ i ] = position;
}

function show_marker( i ) {
  markers[ i ].openPopup();
  map.panTo( positions[ i ] );
  return false;
}

