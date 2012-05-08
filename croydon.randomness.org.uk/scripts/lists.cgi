#!/usr/bin/perl

use strict;
use warnings;

use lib qw(
            /export/home/rgc/perl5/lib/perl5/
            /export/home/rgc/web/vhosts/croydon.randomness.org.uk/scripts/lib/
);
use CGI;
use JSON;
use OpenGuides;
use OpenGuides::Config;
use Template;
use URI::Encode qw( uri_encode );
use WWW::Mechanize;

my $config_file = $ENV{OPENGUIDES_CONFIG_FILE} || "../wiki.conf";
my $config = OpenGuides::Config->new( file => $config_file );
my $guide = OpenGuides->new( config => $config );
my $wiki = $guide->wiki;
my $formatter = $wiki->formatter;
my $base_url = $config->script_url . $config->script_name;
my $agent = WWW::Mechanize->new;
$agent->credentials( "croydon", "rocks" );
my $q = CGI->new;
my %wanted = map { lc( $_ ) => 1 } $q->param( "street" );

# Get all the locales.
my $url = "$base_url?action=index;cat=locales;format=json";
$agent->get( $url );
my $json = $agent->content;
my $locale_data = decode_json( $json );
my %locales = map { my $name = $_->{name}; $name =~ s/^Locale //;
                    $name => $_->{param} } @$locale_data;
delete $locales{Croydon};

# Process them one at a time.
my @streets;
foreach my $locale ( sort keys %locales ) {
  next unless $wanted{ lc( $locale ) };
  $url = "$base_url?action=index;loc=" . uri_encode( $locale ). ";format=json";
  my @nodes;
  $agent->get( $url );
  $json = $agent->content;
  my $data = decode_json( $json );
  foreach my $datum ( @$data ) {
    my $type;
    my $name = $datum->{name};
    my $address = $datum->{node_data}{metadata}{address}[0];
    if ( !$address ) {
        die "$name has no address!";
    }
    my $number = $address;
    $number =~ s/ $locale$//;
    if ( $address !~ m/$number $locale/ ) {
      $type = "other";
    } elsif ( $number =~ /[13579][a-d]?$/ ) {
      $type = "odd";
    } else {
      $type = "even";
    }
    push @nodes, { name => $name,
                   address => $address,
                   number => $number,
                   type => $type };
  }
  my @odds   = grep { $_->{type} eq "odd" }   @nodes;
  my @evens  = grep { $_->{type} eq "even" }  @nodes;
  my @others = grep { $_->{type} eq "other" } @nodes;
  @odds = sort { my $an = $a->{number}; my $bn = $b->{number}; $an =~ s/-.*$//; $bn =~ s/-.*$//; $an =~ s/[a-d]$//; $bn =~ s/[a-d]$//; $an <=> $bn } @odds;
  @evens = sort { my $an = $a->{number}; my $bn = $b->{number}; $an =~ s/-.*$//; $bn =~ s/-.*$//; $an =~ s/[a-d]$//; $bn =~ s/[a-d]$//; $an <=> $bn } @evens;
  @others = sort {$a->{address} cmp $b->{address} } @others;

  push @streets, { name => $locale, odds => \@odds, evens => \@evens,
                   others => \@others };
}

my %tt_vars = ( streets => \@streets );
my $custom_template_path = $config->custom_template_path || "";
my $template_path = $config->template_path;
my $tt = Template->new( { INCLUDE_PATH => ".:$custom_template_path:$template_path"  } );
print $q->header;
$tt->process( "lists.tt", \%tt_vars );
