#!/usr/bin/perl

use strict;
use warnings;

use lib qw(
    /export/home/rgl/web/vhosts/london.randomness.org.uk/scripts/lib/
    /export/home/rgl/perl5/lib/perl5
);

use CGI qw( :standard );
use CGI::Carp qw( fatalsToBrowser );
use Geo::HelmertTransform;
use OpenGuides;
use POSIX;
use RGL::Addons;
use OpenGuides::Config;
use OpenGuides::Utils;
use Template;

my $config_file = $ENV{OPENGUIDES_CONFIG_FILE} || "../wiki.conf";
my $config = OpenGuides::Config->new( file => $config_file );

my $guide = OpenGuides->new( config => $config );
my $wiki = $guide->wiki;
my $formatter = $wiki->formatter;

my %tt_vars = RGL::Addons->get_tt_vars( config => $config );
my $geo_handler = $config->geo_handler;

my $q = CGI->new;

my $locale = $q->param( "locale" );
my $category = $q->param( "category" );
my $os_x = $q->param( "os_x" );
my $os_y = $q->param( "os_y" );
my $os_dist = $q->param( "os_dist" );
my $lat = $q->param( "latitude" );
my $long = $q->param( "longitude" );
my $latlong_dist = $q->param( "latlong_dist" );
my $origin = $q->param( "origin" );
my $origin_dist = $q->param( "origin_dist" );
my $show_map = $q->param( "show_map" );
my ( $min_lat, $max_lat, $min_long, $max_long, $bd_set );
my $total_count; # Everything with missing photo even if not on map.
my %results;
my %seen;

my ( $x, $y, $dist );

my $do_search = $q->param( "do_search" );
if ( $do_search ) {

  if ( $origin && defined $origin_dist ) {
      my %data = $wiki->retrieve_node( $origin );
      if ( $geo_handler == 3 ) {
          my $mx = $data{metadata}{easting}[0];
          my $my = $data{metadata}{northing}[0];
          if ( $mx && $my ) {
              $x = $mx;
              $y = $my;
              $dist = $origin_dist;
          }
      } elsif ( $geo_handler == 1 ) {
          my $mx = $data{metadata}{os_x}[0];
          my $my = $data{metadata}{os_y}[0];
          if ( $mx && $my ) {
              $x = $mx;
              $y = $my;
              $dist = $origin_dist;
          }
      }
  } else {
      if ( $os_x && $os_y && $os_dist && ( $geo_handler == 1 ) ) {
          $x = $os_x;
          $y = $os_y;
          $dist = $os_dist;
      } elsif ( $lat && $long && $latlong_dist && ( $geo_handler == 3 ) ) {
          require Geo::Coordinates::UTM;
          my $zone;
          ($zone, $x, $y ) = 
                     Geo::Coordinates::UTM::latlon_to_utm( $config->ellipsoid, 
                                                           $lat, $long ); 
          $x =~ s/\..*//; # chop off decimal places 
          $y =~ s/\..*//; # - metre accuracy enough
          $dist = $latlong_dist;
      }
  }

  $x =~ s/[^0-9]//g if $x;
  $y =~ s/[^0-9]//g if $y;
  $dist =~ s/[^0-9]//g if $dist;

  my ( $x_name, $y_name );
  if ( $geo_handler == 3 ) {
      $x_name = "easting";
      $y_name = "northing";
  } elsif ( $geo_handler == 1 ) {
      $x_name = "os_x";
      $y_name = "os_y";
  }

  my $dbh = $wiki->store->dbh;
  my $sql = "
  SELECT DISTINCT
       node.name, locale.metadata_value, category.metadata_value, node.text,
       x.metadata_value, y.metadata_value,
       latit.metadata_value, longit.metadata_value,
       address.metadata_value
  FROM node
  LEFT JOIN metadata as img
    ON ( node.id = img.node_id
         AND node.version = img.version
         AND lower( img.metadata_type ) = 'node_image'
       )
  LEFT JOIN metadata as locale
    ON ( node.id = locale.node_id
         AND node.version = locale.version
         AND lower( locale.metadata_type ) = 'locale'
       )
  LEFT JOIN metadata as category
    ON ( node.id = category.node_id
         AND node.version = category.version
         AND lower( category.metadata_type ) = 'category'
       )
  LEFT JOIN metadata as x
    ON ( node.id = x.node_id
         AND node.version = x.version
         AND lower( x.metadata_type ) = '$x_name'
       )
  LEFT JOIN metadata as y
    ON ( node.id = y.node_id
         AND node.version = y.version
         AND lower( y.metadata_type ) = '$y_name'
       )
  LEFT JOIN metadata as latit
    ON ( node.id = latit.node_id
         AND node.version = latit.version
         AND lower( latit.metadata_type ) = 'latitude'
       )
  LEFT JOIN metadata as longit
    ON ( node.id = longit.node_id
         AND node.version = longit.version
         AND lower( longit.metadata_type ) = 'longitude'
       )
  LEFT JOIN metadata as address
    ON ( node.id = address.node_id
         AND node.version = address.version
         AND lower( address.metadata_type ) = 'address'
       )
  WHERE ( img.metadata_value IS NULL
          OR lower( category.metadata_value ) = 'needs new photo' )
  ";

  if ( $locale ) {
    $sql .= " AND lower( locale.metadata_value ) = '$locale'";
  }

  if ( $category ) {
    $sql .= " AND lower( category.metadata_value ) = '$category'";
  }

  if ( $q->param( "exclude_locales" ) ) {
    $sql .= " AND node.name NOT LIKE 'Locale %'";
  }
  if ( $q->param( "exclude_categories" ) ) {
    $sql .= " AND node.name NOT LIKE 'Category %'";
  }

  $sql .= " ORDER BY node.name";

  my $sth = $dbh->prepare( $sql );
  $sth->execute or die $dbh->errstr;

  # If we want to exclude closed places, get a list of them.
  my $exclude_closed = $q->param( "exclude_closed" );
  my %closed;
  if ( $exclude_closed ) {
    %closed = map { $_ => 1 } $wiki->list_nodes_by_metadata(
        metadata_type => "category",
        metadata_value => "now closed",
        ignore_case => 1,
    );
  }

  # Similarly for excluding contributors.
  my $exclude_contributors = $q->param( "exclude_contributors" );
  my %contributors;
  if ( $exclude_contributors ) {
    %contributors = map { $_ => 1 } $wiki->list_nodes_by_metadata(
        metadata_type => "category",
        metadata_value => "contributors",
        ignore_case => 1,
    );
  }

  my $base_url = $config->script_url . $config->script_name . "?";

  while ( my ( $name, $this_locale, $this_category, $content,
               $this_x, $this_y, $this_lat, $this_long, $address)
                                                     = $sth->fetchrow_array ) {
    # We may have already processed this page, if it has more than one locale
    # or category.
    if ( $seen{$name} ) {
        next;
    } else {
        $seen{$name} = 1;
    }

    # If this is a redirect it doesn't count at all.
    if ( $content =~ qr/^\s*#REDIRECT/ ) {
        next;
    }

    # Ditto if it's closed and we're ignoring closed places.
    next if ( $exclude_closed && $closed{$name} );

    # Ditto for contributors.
    next if ( $exclude_contributors && $contributors{$name} );

    # If we're doing a location search, we need geodata.
    if ( $x && $y && $dist ) {
        if ( !$this_x || !$this_y ) {
            next;
        }
        my $this_dist = int( sqrt( ( $x - $this_x )**2 + ( $y - $this_y )**2 )
                             + 0.5 );
        if ( $this_dist > $dist ) {
            next;
        }
    }

    # OK, this should definitely be included in the count.
    $total_count++;

    # But not on the map, if we want a map and it has no coords.
    if ( $show_map ) {
        if ( !$this_lat || !$this_long ) {
            next;
        }
    }

    # OK, we want to include this page; package its data for TT.
    my $param = $formatter->node_name_to_node_param( $name );
    my $this = {
                 name => CGI->escapeHTML( $name ),
                 address => CGI->escapeHTML( $address),
                 param => $param,
               };
    if ( $show_map && defined $this_lat && defined $this_long ) {
        ( $this_long, $this_lat ) = OpenGuides::Utils->get_wgs84_coords(
                                        latitude  => $this_lat,
                                        longitude => $this_long,
                                        config    => $config );
        $this->{wgs84_lat} = $this_lat;
        $this->{wgs84_long} = $this_long;
        $this->{has_geodata} = 1;
        $this->{markertype} = "large_light_red";
        if ( !$bd_set ) {
            $min_lat = $max_lat = $this_lat;
            $min_long = $max_long = $this_long;
            $bd_set = 1;
        } else {
            if ( $this_lat < $min_lat ) {
                $min_lat = $this_lat;
            }
            if ( $this_long < $min_long ) {
                $min_long = $this_long;
            }
            if ( $this_lat > $max_lat ) {
                $max_lat = $this_lat;
            }
            if ( $this_long > $max_long ) {
                $max_long = $this_long;
            }
        }
    }
    $results{$name} = $this;
  }
}

my $any_string = " -- any -- ";

my @localelist = $wiki->list_nodes_by_metadata(
    metadata_type  => "category",
    metadata_value => "locales",
    ignore_case    => 1,
);
@localelist = sort map { s/^Locale //; $_; } @localelist;
$tt_vars{locale_box} = $q->popup_menu( -name   => "locale",
                                       -values => [ "", @localelist ],
                                       -labels => { "" => $any_string,
                                                    map { $_ => $_ }
                                                          @localelist },
                                     );

my @catlist = $wiki->list_nodes_by_metadata(
    metadata_type  => "category",
    metadata_value => "category",
    ignore_case    => 1,
);
@catlist = sort map { s/^Category //; $_; } @catlist;
$tt_vars{category_box} = $q->popup_menu( -name   => "category",
                                         -values => [ "", @catlist ],
                                         -labels => { "" => $any_string,
                                                      map { $_ => $_ }
                                                            @catlist },
                                       );

if ( $geo_handler == 1 ) {
    $tt_vars{os_x_box} = $q->textfield( -name => "os_x", -size => 6,
                                        -maxlength => 6 );
    $tt_vars{os_y_box} = $q->textfield( -name => "os_y", -size => 6,
                                        -maxlength => 6 );
    $tt_vars{os_dist_box} = $q->textfield( -name => "os_dist", -size => 4,
                                           -maxlength => 4 );
} elsif ( $geo_handler == 3 ) {
    $tt_vars{latitude_box} = $q->textfield( -name => "latitude", -size => 10 );
    $tt_vars{longitude_box} = $q->textfield( -name => "longitude", -size => 10 );
    $tt_vars{latlong_dist_box} = $q->textfield( -name => "latlong_dist",
                                                -size => 4, -maxlength => 4 );
}

$tt_vars{exclude_locales_box} = $q->checkbox( -name => "exclude_locales",
  -value => 1, -label => " Exclude locale pages" );
$tt_vars{exclude_categories_box} = $q->checkbox( -name => "exclude_categories",
  -value => 1, -label => " Exclude category pages" );
$tt_vars{exclude_closed_box} = $q->checkbox( -name => "exclude_closed",
  -value => 1, -label => " Exclude places that have now closed" );
$tt_vars{exclude_contributors_box} = $q->checkbox(
  -name => "exclude_contributors", -value => 1,
  -label => " Exclude contributor pages" );
$tt_vars{show_map_box} = $q->checkbox( -name => "show_map", -value => 1,
  -label => " Show results on map (may be slow for large result sets)" );

my $custom_template_path = $config->custom_template_path || "";
my $template_path = $config->template_path;
my $tt = Template->new( { INCLUDE_PATH =>
                                   "$custom_template_path:$template_path"  } );

# Make sure the maps work, and include the total count in case some had to
# be missed off the map.
if ( $show_map ) {
    %tt_vars = (
                 %tt_vars,
                 enable_gmaps        => 1,
                 display_google_maps => 1,
                 show_map            => 1,
                 exclude_navbar      => 1,
                 min_lat             => $min_lat,
                 max_lat             => $max_lat,
                 min_long            => $min_long,
                 max_long            => $max_long,
                 centre_lat          => ( $min_lat + $max_lat ) / 2,
                 centre_long         => ( $min_long + $max_long ) / 2,
                 total_count         => $total_count,
               );
}

# Grab the total number of photos and pages.
my $num_photos = RGL::Addons->get_num_photos( wiki => $wiki );
$tt_vars{num_photos} = $num_photos;
my $num_pages = RGL::Addons->get_page_count( wiki => $wiki );
$tt_vars{percent_photos} = floor( 100 * $num_photos / $num_pages );

%tt_vars = (
             %tt_vars,
             addon_title => "Pages that need a photo",
             geo_handler => $geo_handler,
             results     => [ sort { $a->{name} cmp $b->{name} }
                                   values %results ],
             do_search   => $do_search,
           );

if ( $q->param( "format" ) && $q->param( "format" ) eq "kml" ) {
    $tt_vars{points} = $tt_vars{results};
    $tt_vars{style} = "photo";
    print $q->header( "application/vnd.google-earth.kml+xml" );
    $tt->process( "kml.tt", \%tt_vars );
} else {
    print $q->header;
    $tt->process( "no_image.tt", \%tt_vars ) or die $tt->error;
}
