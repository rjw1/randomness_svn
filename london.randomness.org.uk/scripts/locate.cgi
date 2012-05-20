#!/usr/bin/perl

use strict;
use warnings;

use lib qw(
    /export/home/rgl/web/vhosts/london.randomness.org.uk/scripts/lib/
    /export/home/rgl/perl5/lib/perl5
);
use CGI qw( :standard );
use CGI::Carp qw( fatalsToBrowser );
use OpenGuides;
use OpenGuides::Config;
use OpenGuides::CGI;
use RGL::Addons;
use Template;
use URI::Escape;

my $config_file = $ENV{OPENGUIDES_CONFIG_FILE} || "../wiki.conf";
my $config = OpenGuides::Config->new( file => $config_file );
my $guide = OpenGuides->new( config => $config );

my %tt_vars = RGL::Addons->get_tt_vars( config => $config );

my $q = CGI->new;

$tt_vars{show_search_example} = 1;

my $do_search = $q->param( "Search" );
my $show_map = $q->param( "map" );
my $cat = $q->param( "cat" );
my $loc = $q->param( "loc" );

if ( $do_search || $cat || $loc ) {
  my $redir = $config->script_url . $config->script_name . "?action=index";
  if ( $cat ) {
    $redir .= "&cat=" . uri_escape( $cat );
  }
  if ( $loc ) {
    $redir .= "&loc=" . uri_escape( $loc );
  }
  if ( $show_map ) {
    $redir .= "&format=map";
  }
  print $q->redirect( -uri => $redir, -status => 301 );
  exit 0;
}

my @dropdowns = OpenGuides::CGI->make_index_form_dropdowns(
                  guide => $guide );
$tt_vars{index_form_fields} = \@dropdowns;

$tt_vars{cgi_url} = $config->script_url . $config->script_name;
$tt_vars{addon_title} = "Locale/Category Search";
print $q->header;
my $custom_template_path = $config->custom_template_path || "";
my $template_path = $config->template_path;
my $tt = Template->new( { INCLUDE_PATH => ".:$custom_template_path:$template_path"  } );
$tt->process( "locate.tt", \%tt_vars );
