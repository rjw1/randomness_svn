#!/usr/bin/perl 

eval 'exec /usr/bin/perl  -S $0 ${1+"$@"}'
    if 0; # not running under some shell

use warnings;
use strict;
use lib qw(
   /export/home/rgl/web/vhosts/dev.london.randomness.org.uk/scripts/lib/
   /export/home/rgl/web/vhosts/london.randomness.org.uk/scripts/lib/
   /export/home/rgl/perl5/lib/perl5 );

use sigtrap die => 'normal-signals';
use CGI;
use OpenGuides::Config;
use OpenGuides::CGI;
use OpenGuides::JSON;
use OpenGuides::Utils;
use OpenGuides::Template;

my $config_file = $ENV{OPENGUIDES_CONFIG_FILE} || "wiki.conf";
my $config = OpenGuides::Config->new( file => $config_file );
my $wiki = OpenGuides::Utils->make_wiki_object( config => $config );
my $cgi = CGI->new();
my $action = $cgi->param('action') || '';
my $format = $cgi->param('format') || '';

if ( $action eq "set_preferences" ) {
    set_preferences();
} elsif ( $action eq "show" && $format eq "json" ) {
    my $json_writer = OpenGuides::JSON->new( wiki   => $wiki,
                                             config => $config );
    print "Content-type: text/javascript\n\n";
    print $json_writer->make_prefs_json();
} else {
    show_form();
}

sub set_preferences {
    my %prefs = OpenGuides::CGI->get_prefs_from_hash( $cgi->Vars );
    my $prefs_cookie = OpenGuides::CGI->make_prefs_cookie(
        config => $config,
        %prefs,
    );
    my @cookies = ( $prefs_cookie );
    # If they've asked not to have their recent changes visits tracked,
    # clear any existing recentchanges cookie.
    if ( ! $prefs{track_recent_changes_views} ) {
        my $rc_cookie = OpenGuides::CGI->make_recent_changes_cookie(
            config       => $config,
            clear_cookie => 1,
        );
        push @cookies, $rc_cookie;
    }
    # We have to send the username to OpenGuides::Template because they might
    # have changed it, in which case it won't be in the cookie yet.
    print OpenGuides::Template->output(
        wiki     => $wiki,
        config   => $config,
        template => "preferences.tt",
        cookies  => \@cookies,
        vars     => {
                      not_editable => 1,
                      not_deletable => 1,
                      username => $prefs{username},
                    }
    );
}

sub show_form {
    print OpenGuides::Template->output(
        wiki     => $wiki,
        config   => $config,
        template => "preferences.tt",
	vars     => { 
                      not_editable  => 1,
                      show_form     => 1,
                      not_deletable => 1,
                    }
    );
}
