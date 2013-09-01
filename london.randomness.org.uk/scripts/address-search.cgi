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
use RGL::Addons;
use OpenGuides::Config;
use OpenGuides::Utils;
use Template;

my $config_file = $ENV{OPENGUIDES_CONFIG_FILE} || "../wiki.conf";
my $config = OpenGuides::Config->new( file => $config_file );

my $guide = OpenGuides->new( config => $config );
my $wiki = $guide->wiki;
my $formatter = $wiki->formatter;
my $base_url = $config->script_url . $config->script_name . "?";

my %tt_vars = RGL::Addons->get_tt_vars( config => $config );

my $q = CGI->new;
my $dbh = $wiki->store->dbh;

# Do search if we have the param.
my $address = $q->param( "address" );
if ( $address ) {
    my $sql = "
        SELECT DISTINCT node.name, address.metadata_value
        FROM node
        INNER JOIN metadata as address
          ON ( node.id = address.node_id
               AND node.version = address.version
               AND lower( address.metadata_type ) = 'address'
             )
        WHERE address.metadata_value LIKE ?
        ORDER BY node.name";

    my $sth = $dbh->prepare( $sql );
    $sth->execute( "%" . $address . "%" ) or die $dbh->errstr;

    my @nodes;
    while ( my ( $name, $this_address ) = $sth->fetchrow_array ) {
        my $param = $formatter->node_name_to_node_param( $name );
        push @nodes, {
                       name => CGI->escapeHTML( $name ),
                       address => CGI->escapeHTML( $this_address),
                       url  => $base_url . $param,
                     };
    }
    $tt_vars{nodes} = \@nodes;
    $tt_vars{searching} = 1;
}

$tt_vars{address_box} = $q->textfield( -name => "address", -size => 60 );

my $custom_template_path = $config->custom_template_path || "";
my $template_path = $config->template_path;
my $tt = Template->new( { INCLUDE_PATH =>
                                   "$custom_template_path:$template_path"  } );

%tt_vars = (
             %tt_vars,
             addon_title => "Search by address",
           );

print $q->header;
$tt->process( "address_search.tt", \%tt_vars ) or die $tt->error;
