#!/usr/bin/perl -w

use strict;

use lib qw(
    /export/home/rgc/web/vhosts/croydon.randomness.org.uk/scripts/lib/
    /export/home/rgc/perl5/lib/perl5/
);
use CGC;
use CGI;
#use CGI::Carp qw(fatalsToBrowser);
use Geo::Coordinates::OSGB;
use OpenGuides;
use OpenGuides::CGI;
use OpenGuides::Config;
use POSIX qw( strftime );
use Template;

my $config_file = $ENV{OPENGUIDES_CONFIG_FILE} || "../wiki.conf";
my $config = OpenGuides::Config->new( file => $config_file );
my $guide = OpenGuides->new( config => $config );
my $wiki = $guide->wiki;
my $formatter = $wiki->formatter;
my $q = CGI->new;
my %tt_vars;

# Find out how many months we want to look back.  Default to 6.
my $months = $q->param( "months" ) || 6;

# Find out if we want a map or a list.
my $format = $q->param( "format" );
if ( !$format || $format ne "list" ) {
  $format = "map";
}

# Find out if we want to restrict results to a given radius around us.
my $dist = $q->param( "dist" ) || 0;
my $lat = $q->param( "lat" );
my $long = $q->param( "long" );
my ( $origin_x, $origin_y );
if ( defined $lat && defined $long ) {
  ( $origin_x, $origin_y ) = Geo::Coordinates::OSGB::ll_to_grid( $lat, $long );
} else {
  $dist = 0;
}

# Get all the nodes.
my @nodes = $wiki->list_all_nodes;
my @to_check;

my %to_exclude = map { $_ => 1 } ( "FAQ", "Home", "Tools", "Contact Us", "West Croydon Bus Station", "West Croydon Tram Stop", "West Croydon Station", "Croydon Minster", "Fairfield Halls" );

my $nodes_on_map;

foreach my $node ( @nodes ) {
  next if $node =~ /^Category /;
  next if $node =~ /^Locale /;
  next if $to_exclude{$node};

  my %data = $wiki->retrieve_node( $node );
  next if OpenGuides::Utils->detect_redirect( content => $data{content} ); 

  my $now = strftime( "%B %Y", localtime );
  my $n = CGC->months_since_last_verified( text => $data{content},

                                           date => $now );

  # Only flag things if they've not been checked for N months.
  next if $n > -1 && $n < $months;

  # Don't flag things that are vacant, or things in the meta category.
  my %cats = map { lc( $_ ) => 1 } @{ $data{metadata}{category} };
  next if $cats{vacant} || $cats{meta};

  my %this_node = (
    name => $node,
    param => $formatter->node_name_to_node_param( $node ),
    address => $data{metadata}{address}[0],
  );

  if ( $format eq "map" || $dist ) {
    my ( $wgs84_long, $wgs84_lat )
        = OpenGuides::Utils->get_wgs84_coords(
              latitude  => $data{metadata}{latitude}[0],
              longitude => $data{metadata}{longitude}[0],
              config    => $config );
    if ( defined $wgs84_lat ) {
        $this_node{has_geodata} = 1;
        $this_node{wgs84_lat} = $wgs84_lat;
        $this_node{wgs84_long} = $wgs84_long;
        $nodes_on_map++;

        if ( $dist ) {
          my ( $x, $y ) = Geo::Coordinates::OSGB::ll_to_grid(
                                       $wgs84_lat, $wgs84_long );
          my $this_dist = int( sqrt( ( $origin_x - $x )**2
                                   + ( $origin_y - $y )**2 ) + 0.5 );
          $this_node{dist} = $this_dist;
          next if ( $this_dist > $dist );
        }
    }
  }
  push @to_check, \%this_node;
}

if ( $dist ) {
  @to_check = sort { $a->{dist} <=> $b->{dist} } @to_check;
}

%tt_vars = (
             not_editable  => 1,
             not_deletable => 1,
             deter_robots  => 1,
             nodes         => \@to_check,
             format        => $format,
             cgi_url       => $q->url(),
           );

if ( $format eq "map" ) {
  my %minmaxdata = OpenGuides::Utils->get_wgs84_min_max( nodes => \@to_check );
  if ( scalar %minmaxdata ) {
    %tt_vars = ( %tt_vars, %minmaxdata );
  }
  %tt_vars = ( %tt_vars,
               display_google_maps => 1, # to get the JavaScript in
               show_map => 1,
               no_nodes_on_map => !$nodes_on_map,
             );
}

$tt_vars{format_box} = $q->radio_group(
    -name => "format",
    -values => [ "map", "list" ] );

$tt_vars{months_box} = $q->popup_menu(
    -name => "months",
    -values => [ 1 .. 12 ],
    -labels => { map { $_ => "last checked $_ or more months ago" } ( 1.. 12) }
);

$tt_vars{lat_box} = $q->textfield(
    -name => "lat", -id => "lat_box", -size => 10 );
$tt_vars{long_box} = $q->textfield(
    -name => "long", -id => "long_box", -size => 10 );
$tt_vars{dist_box} = $q->textfield( -name => "dist", -size => 4 );

print $guide->process_template(
                                template => "needs_checking.tt",
                                tt_vars => \%tt_vars,
                              );
