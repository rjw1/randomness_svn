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

print $q->header( "text/plain" );

print "Survey route finder for " . $config->{site_name} . "\n";
print "Bounding box size: $BOUND_BOX\n";

#my $routefile = "/export/home/kake/survey-routes.kml";
#my $routeinfo = XMLin( $routefile )->{Document}{Placemark};

#my $kml_url = "http://maps.google.co.uk/maps/ms?authuser=0&vps=2&ie=UTF8&msa=0&output=kml&msid=210131270935033819755.0004fe8f25aeae360e4c0";
my $kml_url = "https://maps.google.co.uk/maps/ms?authuser=0&vps=2&ie=UTF8&msa=0&output=kml&msid=210131270935033819755.0004feb73dce30bffdd25";
my $mech = WWW::Mechanize->new();
$mech->get( $kml_url );
my $kml = $mech->content;
#print $kml; exit 0;
my $routeinfo = XMLin( $kml )->{Document}{Placemark};
#use Data::Dumper; print Dumper $routeinfo; exit 0;

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
         = Geo::Coordinates::OSGB::ll_to_grid( $lat, $long );
        # Transform WGS84 grid to OSGB grid.
        my ( $x, $y )
         = Geo::Coordinates::OSTN02::ETRS89_to_OSGB36( $wgs84_x, $wgs84_y, 0 );
        push @points, { long => $long, lat => $lat,
                        x => floor( $x ), y => floor( $y ) };
    }
    $routes{$routename} = [ @points ];
}
#use Data::Dumper; print Dumper \%routes; exit 0;

my @route = @{$routes{6}};

my @to_survey;
my %seen;

my $i = 0;
while ( $i < $#route ) {
    # Line segment starts at (x1, y1) and ends at (x2, y2).
    my ( $x1, $y1 ) = ( $route[$i]{x}, $route[$i]{y} );
    my ( $x2, $y2 ) = ( $route[$i+1]{x}, $route[$i+1]{y} );
    my $length = sqrt( ($x1-$x2)**2 + ($y1-$y2)**2 ); # Pythagoras
    print "Start: $x1, $y1 / End: $x2, $y2 / Length: $length\n";

    # Use similar triangles to pick checkpoints $DELTA metres apart along this
    # line segment.  Always include the segment's start point and end point.
    # Non-endpoint checkpoints are unlikely to be integers - is this OK?
    my @checkpoints = ( [ $x1, $y1 ] );
    my $along = $DELTA;
    while ( $along < $length ) {
        push @checkpoints, [ $x1 + ($x2-$x1) * $along / $length,
                             $y1 + ($y2-$y1) * $along / $length ];
        $along += $DELTA;
    }
    push @checkpoints, [ $x2, $y2 ];
    #use Data::Dumper; print Dumper \@checkpoints;

    # Find venues within $BOUND_BOX metres of each checkpoint and push them
    # onto our list.  Also keep hash of which venues are already on the list.
    foreach my $point ( @checkpoints ) {
      my ( $x, $y ) = @$point;
      print "Looking for venues within $BOUND_BOX metres of ($x, $y)\n";
      my @venues = $locator->find_within_distance(
          x => $x, y => $y, metres => $BOUND_BOX );
      foreach my $venue ( @venues ) {
        print "Found $venue\n";
        next if $seen{$venue};
        push @to_survey, $venue;
        $seen{$venue} = 1;
      }
    }

    #use Data::Dumper; print Dumper \@to_survey;
    #last;
    $i++;
}

use Data::Dumper; print Dumper \@to_survey;
