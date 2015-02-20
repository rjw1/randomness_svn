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
use Template;
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

# The map for editing is at:
# http://umap.openstreetmap.fr/en/map/cgc-survey_29724
# GeoJSON version at http://umap.openstreetmap.fr/en/map/29724/geojson/
# See datalayer stuff in the JSON to get the json_url below.
my $json_url = "http://umap.openstreetmap.fr/en/datalayer/61278/";

my @route = get_route( json_url => $json_url );
my @to_survey = get_survey_venues( route => \@route );
exit 0 if $plain;

# Package the data for the template.
my %tt_vars = ( nodes => \@to_survey );
my $custom_template_path = $config->custom_template_path || "";
my $template_path = $config->template_path;
my $tt = Template->new( {
               INCLUDE_PATH => ".:$custom_template_path:$template_path" } );
print $q->header;
$tt->process( "surveys.tt", \%tt_vars );


# Pass in a GeoJSON URL and get back an array of points relating to
# the first LineString found in the data.  Each point is a hashref
# containing lat, long, x, and y - lat and long come directly from the
# KML, whereas x and y are the results of transforming to OSGB.

sub get_route {
    my %args = @_;
    my $json_url = $args{json_url};

    my $mech = WWW::Mechanize->new();
    $mech->get( $json_url );
    my $json = $mech->content;
    #if ( $plain ) { print $json; exit 0; }

    my $routeinfo = decode_json( $json );
    #if ( $plain ) { use Data::Dumper; print Dumper $routeinfo; exit 0; }

    my $coords = $routeinfo->{features}[0]{geometry}{coordinates};
    #if ( $plain ) { use Data::Dumper; print Dumper $coords; exit 0; }

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

    #if ( $plain ) { use Data::Dumper; print Dumper \@points; exit 0; }

    return @points;
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
