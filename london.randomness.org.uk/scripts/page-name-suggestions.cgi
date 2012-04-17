#!/usr/bin/perl

use strict;
use warnings;

use lib qw( /export/home/rgl/perl5/lib/perl5 );
use lib qw( /export/home/rgl/web/vhosts/london.randomness.org.uk/scripts/lib/ );

use CGI qw( :standard );
use CGI::Carp qw( fatalsToBrowser );
use Data::Dumper;
use OpenGuides;
use OpenGuides::Config;
use RGL::Addons;

my $config_file = $ENV{OPENGUIDES_CONFIG_FILE} || "../wiki.conf";
my $config = OpenGuides::Config->new( file => $config_file );

my $guide = OpenGuides->new( config => $config );
my $wiki = $guide->wiki;
my $formatter = $wiki->formatter;

my $q = CGI->new;
print $q->header;

if ( $q->param( "page" ) ) {
    find_pages();
} else {
    print "<p>No page name parameter supplied; can't find anything!</p>\n";
}

sub find_pages {
    my $node_param = $q->param( "page" );
    my $node_name = $formatter->node_param_to_node_name( $node_param );
    my $full_script_url = $config->script_url . $config->script_name;

    # If we have more than 5 consonants (to rule out postcodes), do a
    # fuzzy title match.
    my %fuzzy;
    my $len = $node_name;
    $len =~ s/[^bcdfghjklmnpqrstvwxyz]//gi;
    if ( length( $len ) > 5 ) {
      %fuzzy = $wiki->fuzzy_title_match( $node_name );
    }

    my @trunc = RGL::Addons->search_truncated_node_names( wiki => $wiki,
                  node => $node_name );
    my %trunc_hash = map { $_ => 1 } @trunc;

    my %poss_hash = ( %fuzzy, %trunc_hash );
    my @possibles = sort keys %poss_hash;

    if ( scalar @possibles ) {
      print "<ul>\n";
      foreach my $node ( @possibles ) {
        print "<li><a href=\"$full_script_url?"
              . $formatter->node_name_to_node_param( $node )
              . '">'
              . $q->escapeHTML( $node )
              . "</a></li>\n"
      }
      print "</ul>\n";
    } else {
      print "<p>No possibilities found, sorry.</p>"
    }
}
