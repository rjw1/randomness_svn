#!/usr/bin/perl -w

use strict;

use lib qw(
            /export/home/pubology/perl5/lib/perl5/
          );

use CGI;
use CGI::Carp qw( fatalsToBrowser );
use Template;

my $HOME = "/export/home/pubology";
my $base_url = "http://www.pubology.co.uk/";

my $q = CGI->new;

# Set up template stuff
my $tt_config = {
  INCLUDE_PATH => "$HOME/templates/",
};
my $tt = Template->new( $tt_config ) or croak Template->error;

my %tt_vars = (
                base_url => $base_url,
                edit_url => $base_url . "admin/edit-static-page.cgi",
              );

print $q->header;
$tt->process( "admin_home.tt", \%tt_vars ) || croak $tt->error;
