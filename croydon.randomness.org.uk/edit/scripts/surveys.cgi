#!/usr/bin/perl -w

use strict;

use lib qw(
    /export/home/rgc/web/vhosts/croydon.randomness.org.uk/scripts/lib/
    /export/home/rgc/perl5/lib/perl5/
);

use CGI;
use Geo::Coordinates::OSGB;
use Geo::Coordinates::OSTN02;
use JSON;
use OpenGuides;
use OpenGuides::Config;
use POSIX;
use Wiki::Toolkit::Plugin::Locator::Grid;
use WWW::Mechanize;
use XML::Simple;

my $MAX_ROAD_WIDTH = 20;
my $DELTA = 5;
my $BOUND_BOX = ceil( 0.5 * sqrt( $DELTA**2 + 4*($MAX_ROAD_WIDTH**2) ) );

my $config_file = $ENV{OPENGUIDES_CONFIG_FILE} || "../wiki.conf";
my $config = OpenGuides::Config->new( file => $config_file );
my $guide = OpenGuides->new( config => $config );
my $wiki = $guide->wiki;
my $formatter = $wiki->formatter;
my $locator = Wiki::Toolkit::Plugin::Locator::Grid->new( x => "os_x", y => "os_y" );
$wiki->register_plugin( plugin => $locator );
my $q = CGI->new;

my $plain = $q->param( "plain" ) || 0;

if ( $plain ) {
  print $q->header( "text/plain" );
  print "Survey route finder for " . $config->{site_name} . "\n";
  print "Bounding box size: $BOUND_BOX\n";
}

my $kml_url = "https://maps.google.co.uk/maps/ms?authuser=0&vps=2&ie=UTF8&msa=0&output=kml&msid=210131270935033819755.0004fec30bd5ef5150821";

my %routes = get_routes( kml_url => $kml_url );
my @route = @{$routes{6}};
my @to_survey = get_survey_venues( route => \@route );
exit 0 if $plain;

# Pass in a KML URL and get back a hash where the keys are the route names
# and the values are refs to arrays of points, with each point being a
# hashref containing lat, long, x, and y - lat and long come directly from
# the KML, whereas x and y are the results of transforming to OSGB.
sub get_routes {
    my %args = @_;
    my $kml_url = $args{kml_url};

    my $mech = WWW::Mechanize->new();
    $mech->get( $kml_url );
    my $kml = $mech->content;
    #if ( $plain ) { print $kml; exit 0; }
    my $routeinfo = XMLin( $kml )->{Document}{Placemark};
    #if ( $plain ) { use Data::Dumper; print Dumper $routeinfo; exit 0; }

    my %routes;
    foreach my $routename ( keys %$routeinfo ) {
        my $coordstr = $routeinfo->{$routename}{LineString}{coordinates};
        $coordstr =~ s/^\s+//;
        my @pointstrs = split /\s+/, $coordstr;
        my @points;
        foreach my $pointstr ( @pointstrs ) {
            my ( $long, $lat ) = split ',', $pointstr;
            # Transform lat/long to grid based on WGS84.
            my ( $wgs84_x, $wgs84_y )
             = Geo::Coordinates::OSGB::ll_to_grid( $lat, $long, 'WGS84' );
            # Transform WGS84 grid to OSGB grid.
            my ( $x, $y ) = Geo::Coordinates::OSTN02::ETRS89_to_OSGB36(
                                $wgs84_x, $wgs84_y, 0 );
            push @points, { long => $long, lat => $lat,
                            x => floor( $x ), y => floor( $y ) };
        }
        $routes{$routename} = [ @points ];
    }

    #if ( $plain ) { use Data::Dumper; print Dumper \%routes; exit 0; }

    return %routes;
}

# Returns a list of names, in order.
sub get_survey_venues {
  my %args = @_;
  my @route = @{$args{route}};

  my @to_survey;
  my %seen;

  my $i = 0;
  while ( $i < $#route ) {
    # Line segment starts at (x1, y1) and ends at (x2, y2).
    my ( $x1, $y1 ) = ( $route[$i]{x}, $route[$i]{y} );
    my ( $x2, $y2 ) = ( $route[$i+1]{x}, $route[$i+1]{y} );
    my $length = sqrt( ($x1-$x2)**2 + ($y1-$y2)**2 ); # Pythagoras
    print "Start: $x1, $y1 / End: $x2, $y2 / Length: $length\n" if $plain;

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
    #if ( $plain ) { use Data::Dumper; print Dumper \@checkpoints; }

    # Find venues within $BOUND_BOX metres of each checkpoint and push them
    # onto our list.  Keep hash of which venues are already on the list.
    foreach my $point ( @checkpoints ) {
      my ( $x, $y ) = @$point;
      print "Looking for venues within $BOUND_BOX metres of ($x, $y)\n"
          if $plain;
      my @venues = $locator->find_within_distance(
          x => $x, y => $y, metres => $BOUND_BOX );
      foreach my $venue ( @venues ) {
        print "Found $venue\n" if $plain;
        next if $seen{$venue};
        push @to_survey, $venue;
        $seen{$venue} = 1;
      }
    }

    #if ( $plain ) { use Data::Dumper; print Dumper \@to_survey; }
    #last;
    $i++;
  }

  if ( $plain ) { use Data::Dumper; print Dumper \@to_survey; }
  return @to_survey;
}
