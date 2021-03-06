#!/usr/bin/perl 

eval 'exec /usr/bin/perl  -S $0 ${1+"$@"}'
    if 0; # not running under some shell

use warnings;
use strict;
use lib qw(
            /export/home/rgc/web/vhosts/croydon.randomness.org.uk/scripts/lib/
            /export/home/rgc/perl5/lib/perl5/
          );
use sigtrap die => 'normal-signals';
use CGI;
use OpenGuides::Config;
use OpenGuides::Search;

my $config_file = $ENV{OPENGUIDES_CONFIG_FILE} || "wiki.conf";
my $config = OpenGuides::Config->new( file => $config_file );
my $search = OpenGuides::Search->new( config => $config );
my %vars = CGI::Vars();
$search->run( vars => \%vars );
