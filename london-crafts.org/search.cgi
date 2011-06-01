#!/usr/bin/perl 

eval 'exec /usr/local/bin/perl  -S $0 ${1+"$@"}'
    if 0; # not running under some shell
use lib qw( /export/home/lc/perl5/lib/perl5 );

use warnings;
use strict;

use CGI;
use OpenGuides::Config;
use OpenGuides::Search;

my $config_file = $ENV{OPENGUIDES_CONFIG_FILE} || "wiki.conf";
my $config = OpenGuides::Config->new( file => $config_file );
my $search = OpenGuides::Search->new( config => $config );
my %vars = CGI::Vars();
$search->run( vars => \%vars );
