package CGC::Routes;

use strict;

use Geo::Coordinates::OSGB;
use Geo::Coordinates::OSTN02;
use JSON;
use POSIX;
use Wiki::Toolkit::Plugin::Locator::Grid;
use WWW::Mechanize;

=head1 NAME

CGC::Routes - Routing-related utilities for the Completists' Guide to Croydon.

=head1 DESCRIPTION

Routing-related utilities for the Completists' Guide to Croydon.

=head1 METHODS

=over

=item B<foo>

Pass in a GeoJSON URL and get back an array of points relating to
the first LineString found in the data.  Each point is a hashref
containing lat, long, x, and y - lat and long come directly from the
KML, whereas x and y are the results of transforming to OSGB.

=cut

sub get_route_from_json_url {
    my ( $class, %args ) = @_;
    my $json_url = $args{json_url};

    my $mech = WWW::Mechanize->new();
    $mech->get( $json_url );
    my $json = $mech->content;

    my $routeinfo = decode_json( $json );

    my $coords = $routeinfo->{features}[0]{geometry}{coordinates};

    my @points;
    foreach my $pair ( @$coords ) {
        my ( $long, $lat ) = @$pair;
        # Transform lat/long to grid based on WGS84.
        my ( $wgs84_x, $wgs84_y )
             = Geo::Coordinates::OSGB::ll_to_grid( $lat, $long, 'WGS84' );
        # Transform WGS84 grid to OSGB grid.
        my ( $x, $y ) = Geo::Coordinates::OSTN02::ETRS89_to_OSGB36(
                                $wgs84_x, $wgs84_y, 0 );
        push @points, { long => $long, lat => $lat,
                        x => floor( $x ), y => floor( $y ) };
    }

    return @points;
}

# Returns a list of names, in order.
sub get_nodes_from_route {
  my ( $class, %args ) = @_;

  my $MAX_ROAD_WIDTH = 20;
  my $DELTA = 5;
  my $BOUND_BOX = ceil( 0.5 * sqrt( $DELTA**2 + 4*($MAX_ROAD_WIDTH**2) ) );

  my @route = @{$args{route}};
  my $guide = $args{guide};
  my $wiki = $guide->wiki;
  my $locator = Wiki::Toolkit::Plugin::Locator::Grid->new(
                  x => "os_x", y => "os_y" );
  $wiki->register_plugin( plugin => $locator );

  my @to_survey;
  my %seen;

  my $i = 0;
  while ( $i < $#route ) {
    # Line segment starts at (x1, y1) and ends at (x2, y2).
    my ( $x1, $y1 ) = ( $route[$i]{x}, $route[$i]{y} );
    my ( $x2, $y2 ) = ( $route[$i+1]{x}, $route[$i+1]{y} );
    my $length = sqrt( ($x1-$x2)**2 + ($y1-$y2)**2 ); # Pythagoras

    # Use similar triangles to pick checkpoints $DELTA metres apart along
    # this line segment.  Always include the segment's start point and end
    # point.  Non-endpoint checkpoints are unlikely to be integers - OK?
    my @checkpoints = ( [ $x1, $y1 ] );
    my $along = $DELTA;
    while ( $along < $length ) {
      push @checkpoints, [ $x1 + ($x2-$x1) * $along / $length,
                           $y1 + ($y2-$y1) * $along / $length ];
      $along += $DELTA;
    }
    push @checkpoints, [ $x2, $y2 ];

    # Find venues within $BOUND_BOX metres of each checkpoint and push them
    # onto our list.  Keep hash of which venues are already on the list.
    foreach my $point ( @checkpoints ) {
      my ( $x, $y ) = @$point;
      my @venues = $locator->find_within_distance(
          x => $x, y => $y, metres => $BOUND_BOX );
      foreach my $venue ( @venues ) {
        next if $seen{$venue};
        push @to_survey, $venue;
        $seen{$venue} = 1;
      }
    }

    $i++;
  }

  return @to_survey;
}

=back

=cut

1;
