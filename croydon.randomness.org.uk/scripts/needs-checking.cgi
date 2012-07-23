#!/usr/bin/perl -w

use strict;

use lib qw(
    /export/home/rgc/web/vhosts/croydon.randomness.org.uk/scripts/lib/
    /export/home/rgc/perl5/lib/perl5/
);
use CGC;
use CGI;
#use CGI::Carp qw(fatalsToBrowser);
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

# Get all the nodes.
my @nodes = $wiki->list_all_nodes;
my @to_check;

my %to_exclude = map { $_ => 1 } ( "FAQ", "Home", "Tools", "West Croydon Bus Station", "West Croydon Tram Stop" );

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

  # Only flag things if they've not been checked for 6 months.
  next if $n > -1 && $n < $months;

  # Don't flag things that have the same name and address (these are vacant).
  my $address = $data{metadata}{address}[0];
  next if $node eq $address;

  my %this_node = (
    name => $node,
    param => $formatter->node_name_to_node_param( $node ),
    address => $address,
  );

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
  }
  push @to_check, \%this_node;
}

%tt_vars = (
             not_editable  => 1,
             not_deletable => 1,
             deter_robots  => 1,
             nodes         => \@to_check,
             no_nodes_on_map => !$nodes_on_map,
           );

my %minmaxdata = OpenGuides::Utils->get_wgs84_min_max( nodes => \@to_check );
if ( scalar %minmaxdata ) {
  %tt_vars = ( %tt_vars, %minmaxdata );
}
$tt_vars{display_google_maps} = 1; # to get the JavaScript in
$tt_vars{show_map} = 1;

print $guide->process_template(
                                template => "needs_checking.tt",
                                tt_vars => \%tt_vars,
                              );
