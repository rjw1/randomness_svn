#!/usr/bin/perl

use strict;
use warnings;

use lib qw( /export/home/rgl/web/vhosts/london.randomness.org.uk/scripts/lib/ );
use lib qw( /export/home/rgl/perl5/lib/perl5 );

use CGI qw( :standard );
use CGI::Carp qw( fatalsToBrowser );
use OpenGuides;
use RGL::Addons;
use OpenGuides::Config;
use Template;
use Wiki::Toolkit::Plugin::Locator::Grid;

my $config_file = $ENV{OPENGUIDES_CONFIG_FILE} || "../wiki.conf";
my $config = OpenGuides::Config->new( file => $config_file );

my $guide = OpenGuides->new( config => $config );
my $wiki = $guide->wiki;
my $formatter = $wiki->formatter;
my $dbh = $wiki->store->dbh;
my $locator = Wiki::Toolkit::Plugin::Locator::Grid->new( x => "os_x", y => "os_y" );
$wiki->register_plugin( plugin => $locator );

my %tt_vars = RGL::Addons->get_tt_vars( config => $config );

my $q = CGI->new;

my %all_criteria = (
                     garden    => "beer garden",
                     realale   => "real ale",
                     realcider => "real cider",
                     gbg       => "good beer guide",
                     wifi      => "free wireless",
                     food      => "pub food",
                     barsnacks => "bar snacks",
                     thai      => "thai food",
                     room      => "function room",
                     pool      => "pool table",
                     river     => "river view",
                     fire      => "open fire",
                     step_free => "step-free access",
                     accessible_loo => "accessible toilet",
                     quiz      => "pub quiz",
                     quiz_mon  => "pub quiz on mondays",
                     quiz_tue  => "pub quiz on tuesdays",
                     quiz_wed  => "pub quiz on wednesdays",
                     quiz_thu  => "pub quiz on thursdays",
                     quiz_sun  => "pub quiz on sundays",
                   );

setup_form_variables();

if ( $q->param( "Search" ) ) {
  $tt_vars{doing_search} = 1;
  my @dbparams;
  my $locale = $q->param( "locale" );
  my $district = $q->param( "postal_district" );
  my $tube = $q->param( "tube" );
  my %criteria;

  foreach my $criterion ( keys %all_criteria ) {
    $criteria{$criterion} = $q->param( $criterion );
  }

  my %candidates;
  if ( $tube ) {
    my @cand_arr = $locator->find_within_distance(
        node => $tube,
        metres => $q->param( "tube_distance" ) || 750,
    );
    %candidates = map { $_ =>1 } @cand_arr;
  }

  my $sql = "
SELECT node.name, summary.metadata_value FROM node
INNER JOIN metadata as pub
  ON ( node.id = pub.node_id AND node.version = pub.version
       AND lower(pub.metadata_type) = 'category'
       AND lower(pub.metadata_value) = 'pubs'
     )
INNER JOIN metadata as summary
  ON ( node.id = summary.node_id AND node.version = summary.version
       AND lower( summary.metadata_type ) = 'summary'
     )
";

  if ( $locale || $district ) {
    $sql .= "
INNER JOIN metadata as locale
  ON ( node.id = locale.node_id AND node.version = locale.version
       AND lower(locale.metadata_type) = 'locale'
       AND lower(locale.metadata_value) = ? )
";
    if ( $locale ) {
      push @dbparams, lc( $locale );
    } else {
      push @dbparams, lc( $district );
    }
  }

  foreach my $criterion ( keys %all_criteria ) {
    if ( $criteria{$criterion} ) {
      $sql .= "
INNER JOIN metadata AS $criterion
  ON ( node.id = $criterion.node_id AND node.version = $criterion.version
       AND lower($criterion.metadata_type) = 'category'
       AND lower($criterion.metadata_value) = ? )
";
      push @dbparams, lc( $all_criteria{$criterion} );
    }
  }

  $sql .= " ORDER BY name";

  $tt_vars{sql} = $q->escapeHTML( $sql );

  my $sth = $dbh->prepare( $sql );
  $sth->execute( @dbparams ) or die $dbh->errstr;

  my @pubs;
  while ( my ( $name, $summary ) = $sth->fetchrow_array ) {
    if ( !$tube or $candidates{$name} ) {
      my $param = $formatter->node_name_to_node_param( $name );
      push @pubs, { name => $name, param => $param, summary => $summary };
    }
  }

  $tt_vars{pubs} = \@pubs;
}

# Do the template stuff.
my $custom_template_path = $config->custom_template_path || "";
my $template_path = $config->template_path;
my $tt = Template->new( { INCLUDE_PATH =>
                                   "$custom_template_path:$template_path"  } );
%tt_vars = (
             %tt_vars,
             addon_title => "Pub search",
             self_url => $q->url( -full => 1 ),
           );

print $q->header;
$tt->process( "pubsearch.tt", \%tt_vars );

sub setup_form_variables {

  $tt_vars{tube_distance_box} = $q->popup_menu( -name   => "tube_distance",
                                                -id     => "tube_distance",
                                         -values => [ 500, 750, 1000, 1500,
                                                      2000 ],
                                         -labels => { 500 => "500m",
                                                      750 => "750m",
                                                      1000 => "1km",
                                                      1500 => "1.5km",
                                                      2000 => "2km",
                                                    },
                                       );

  # Find all locales that have pubs in.
  my $sql = "
  SELECT DISTINCT locale.metadata_value FROM node
  INNER JOIN metadata as pub
    ON ( node.id=pub.node_id
         AND node.version=pub.version
         AND lower(pub.metadata_type) = 'category'
         AND lower(pub.metadata_value) = 'pubs'
       )
  INNER JOIN metadata as locale
    ON ( node.id = locale.node_id
         AND node.version = locale.version
         AND lower(locale.metadata_type) = 'locale'
       )
  ";

  my $sth = $dbh->prepare( $sql );
  $sth->execute or die $dbh->errstr;

  my %locales;
  my %postal_districts;
  while ( my ( $locale ) = $sth->fetchrow_array ) {
    if ( $locale =~ /^[A-Z][A-Z]?[0-9][0-9]?$/ ) {
      $postal_districts{$locale} = 1;
    } else {
      $locales{$locale} = 1;
    }
  }

  my $any_string = " -- any -- ";
  my @localelist = sort keys %locales;
  $tt_vars{locale_box} = $q->popup_menu( -name   => "locale", -id => "locale",
                                         -values => [ "", @localelist ],
                                         -labels => { "" => $any_string,
                                                      map { $_ => $_ }
                                                            @localelist },
                                       );

  my @postallist = sort keys %postal_districts;
  $tt_vars{postal_district_box} =
                         $q->popup_menu( -name   => "postal_district",
                                         -id     => "postal_district",
                                         -values => [ "", @postallist ],
                                         -labels => { "" => $any_string,
                                                      map { $_ => $_ }
                                                            @postallist },
                                       );

  my %checkboxes;
  foreach my $criterion ( keys %all_criteria ) {
    $checkboxes{$criterion} = $q->checkbox( -name => $criterion,
                                            -id => $criterion,
                                            -value => 1, -label => "" );
  }

  $tt_vars{checkboxes} = \%checkboxes;

  $tt_vars{tube_box} = RGL::Addons->get_tube_dropdown( guide => $guide, q => $q );
}
