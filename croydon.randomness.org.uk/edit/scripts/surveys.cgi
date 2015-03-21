#!/usr/bin/perl -w

use strict;

use lib qw(
    /export/home/rgc/web/vhosts/croydon.randomness.org.uk/scripts/lib/
    /export/home/rgc/perl5/lib/perl5/
);

use CGC::Routes;
use CGI;
use OpenGuides;
use OpenGuides::Config;
use Template;

my $config_file = $ENV{OPENGUIDES_CONFIG_FILE} || "../wiki.conf";
my $config = OpenGuides::Config->new( file => $config_file );
my $guide = OpenGuides->new( config => $config );
my $q = CGI->new;

# The map for editing is at:
# http://umap.openstreetmap.fr/en/map/cgc-survey_29724
# GeoJSON version at http://umap.openstreetmap.fr/en/map/29724/geojson/
# See datalayer stuff in the JSON to get the json_url below.
my $json_url = "http://umap.openstreetmap.fr/en/datalayer/61278/";

my @route = CGC::Routes->get_route_from_json_url( json_url => $json_url );
my @to_survey = CGC::Routes->get_nodes_from_route(
                  guide => $guide, route => \@route );

# Package the data for the template.
my %tt_vars = ( nodes => \@to_survey );
my $custom_template_path = $config->custom_template_path || "";
my $template_path = $config->template_path;
my $tt = Template->new( {
               INCLUDE_PATH => ".:$custom_template_path:$template_path" } );
print $q->header;
$tt->process( "surveys.tt", \%tt_vars );
