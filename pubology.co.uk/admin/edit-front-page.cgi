#!/usr/bin/perl -w

use strict;

use lib qw(
            /export/home/pubology/perl5/lib/perl5/
          );

use CGI;
use CGI::Carp qw( fatalsToBrowser );

my $base_url = "http://www.pubology.co.uk/";

my $q = CGI->new;
print $q->redirect( $base_url . "admin/edit-static-page.cgi?page=front" );
