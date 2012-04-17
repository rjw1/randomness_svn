#!/usr/bin/perl

use strict;
use warnings;

use lib qw( /export/home/rgl/web/vhosts/london.randomness.org.uk/scripts/lib/ );
use lib qw( /export/home/rgl/perl5/lib/perl5 );
use CGI qw( :standard );
use CGI::Carp qw( fatalsToBrowser );
use OpenGuides;
use OpenGuides::Config;
use OpenGuides::Utils;
use POSIX;
use RGL::Addons;
use Template;
use Wiki::Toolkit::Plugin::Locator::Grid;
use Wiki::Toolkit::Plugin::Categoriser;

my $config_file = $ENV{OPENGUIDES_CONFIG_FILE} || "../wiki.conf";
my $config = OpenGuides::Config->new( file => $config_file );

my $guide = OpenGuides->new( config => $config );
my $wiki = $guide->wiki;
my $formatter = $wiki->formatter;

#my %node = $wiki->retrieve_node( "West Croydon Station" );
#use Data::Dumper; print Dumper \%node;

my %tt_vars = RGL::Addons->get_tt_vars( config => $config );

my $q = CGI->new;

$tt_vars{self_url} = $q->url( -relative );
$tt_vars{show_search_example} = 1;
setup_form_fields();

my $do_search = $q->param( "Search" );
my $cat = $q->param( "cat" );
my $x = $q->param( "x" );
my $y = $q->param( "y" );
my $metres = $q->param( "m" );

if ( $do_search && ( !$x || !$y || !$metres ) ) {
  $tt_vars{error_message} = "Sorry!  You need to choose a point of origin "
    . "and a distance for this search to work.";
} elsif ( $do_search && ( $metres > 5000 ) ) {
  $tt_vars{error_message} = "Sorry!  Distance must be 5000 metres or less.";
} elsif ( $do_search ) {
  $tt_vars{show_search_example} = 0;
  my $small_pointers = $q->param( "small_pointers" ) || 0;
  my $show_map = $q->param( "map" );

  $tt_vars{do_search} = 1;
  $tt_vars{cat} = $cat;
  $tt_vars{x} = $x;
  $tt_vars{y} = $y;
  $tt_vars{metres} = $metres;

  my $base_url = $config->script_url . $config->script_name;
  $tt_vars{cat_link} = $base_url . "?" . $formatter->node_name_to_node_param(
                       "Category " . $cat );

  my $markertype;
  if ( $small_pointers ) {
    $markertype = "small_light_red";
  } else {
    $markertype = "large_light_red";
  }

  # set up plugins
  my $locator = Wiki::Toolkit::Plugin::Locator::Grid->new(
                   x => "os_x", y => "os_y" );
  $wiki->register_plugin( plugin => $locator );
  my $categoriser = Wiki::Toolkit::Plugin::Categoriser->new;
  $wiki->register_plugin( plugin => $categoriser );

  # returns a list of node names
  my @within = $locator->find_within_distance( x => $x, y => $y,
                                               metres => $metres );

  my @results;
  my ( $min_lat, $max_lat, $min_long, $max_long, $bd_set );
  foreach my $node ( @within ) {
    if ( $categoriser->in_category( category => lc( $cat ),
                                          node => $node ) ) {
      my %info = $wiki->retrieve_node( $node );
      my $url = $base_url . "?" . $formatter->node_name_to_node_param( $node );
      my $lat = $info{metadata}{latitude}[0];
      my $long = $info{metadata}{longitude}[0];
      my $dist = ceil ( sqrt(   ( $info{metadata}{os_x}[0] - $x )**2
                              + ( $info{metadata}{os_y}[0] - $y )**2 ) );
      if ( $show_map ) {
        # I still hate that I have to do this.
        ( $long, $lat ) = OpenGuides::Utils->get_wgs84_coords(
                                        latitude  => $lat,
                                        longitude => $long,
                                        config    => $config );
      }
      push @results, {
        name => $node,
        url => $url,
        lat => $lat,
        long => $long,
        dist => $dist,
        markertype => $markertype,
      };
      if ( !$bd_set ) {
        $min_lat = $max_lat = $lat;
        $min_long = $max_long = $long;
        $bd_set = 1;
      } else {
        if ( $lat < $min_lat ) {
          $min_lat = $lat;
        }
        if ( $long < $min_long ) {
          $min_long = $long;
        }
        if ( $lat > $max_lat ) {
          $max_lat = $lat;
        }
        if ( $long > $max_long ) {
          $max_long = $long;
        }
      }
    }

    if ( $show_map ) {
      @results = sort { $a->{name} cmp $b->{name} } @results;
    } else {
      @results = sort { $a->{dist} <=> $b->{dist} } @results;
    }

    $tt_vars{results} = \@results;

    if ( $show_map ) {
      %tt_vars = (
                   %tt_vars,
                   min_lat             => $min_lat,
                   max_lat             => $max_lat,
                   min_long            => $min_long,
                   max_long            => $max_long,
                   exclude_navbar      => 1,
                   enable_gmaps        => 1,
                   display_google_maps => 1,
                   show_map            => 1,
                   lat                 => ( $min_lat + $max_lat ) / 2,
                   long                => ( $min_long + $max_long ) / 2,
                 );
    }
  }
}

$tt_vars{addon_title} = "Things Nearby Search";
print $q->header;
my $custom_template_path = $config->custom_template_path || "";
my $template_path = $config->template_path;
my $tt = Template->new( { INCLUDE_PATH => ".:$custom_template_path:$template_path"  } );
$tt->process( "nearby.tt", \%tt_vars );

sub setup_form_fields {
  my @categories = $wiki->list_nodes_by_metadata(
    metadata_type  => "category",
    metadata_value => "category",
    ignore_case    => 1,
  );
  @categories = map { s/^Category //; $_; } @categories;
  my %tmphash = map { $_ => 1 } @categories;
  for my $key ( ( "Breweries", "Category", "Drink", "Food", "Locales", "Meta", "Now Closed", "Postal Districts", "Pub Chains", "Pub Crawls", "Streets", "Travel", "Wifi" ) ) {
    delete $tmphash{ $key };
  }
  @categories = sort( keys %tmphash );

  $tt_vars{catbox} = $q->popup_menu( -name   => "cat",
                                -values => [ "", @categories ],
                                -labels => { "" => " -- anything -- ",
                                             map { $_ => $_ } @categories }
                              );

  $tt_vars{mbox} = $q->textfield( -name => "m", -size => 4, -maxlength => 4 );
  $tt_vars{xbox} = $q->textfield( -name => "x", -size => 6, -maxlength => 6 );
  $tt_vars{ybox} = $q->textfield( -name => "y", -size => 6, -maxlength => 6 );

  $tt_vars{show_map_box} = $q->checkbox( -name => "map",
                                         -value => 1, label => "" );
  $tt_vars{small_pointers_box} = $q->checkbox( -name => "small_pointers",
                                               -value => 1, label => "" );
}
