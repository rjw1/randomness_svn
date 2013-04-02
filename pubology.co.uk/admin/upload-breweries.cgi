#!/usr/bin/perl -w

use strict;

use lib qw(
            /export/home/pubology/lib/
            /export/home/pubology/perl5/lib/perl5/
          );

use CGI;
use CGI::Carp qw( fatalsToBrowser );
use Config::Tiny;
use File::Copy;
use POSIX qw( strftime );
use PubSite;
use Template;

my $HOME = "/export/home/pubology";
my $base_dir = "$HOME/web/vhosts/pubology.co.uk/";
my $base_url = "http://www.pubology.co.uk/";

my $q = CGI->new;
my $cgi_url = $q->url();
if ( $cgi_url !~ /www/ ) {
  $cgi_url =~ s|http://|http://www.|;
}

# Set up template stuff
my $tt_config = {
  INCLUDE_PATH => "$HOME/templates/",
  OUTPUT_PATH => $base_dir,
};
my $tt = Template->new( $tt_config ) or croak Template->error;

if ( !$q->param( "Upload" ) ) {
  print_form_and_exit();
}

# Make sure we actually have a CSV file.
my $tmpfile = $q->param( "csv" );
if ( $q->param( "Upload" ) && !$tmpfile ) {
  print_form_and_exit( errmsg => "<p>Must supply a CSV file.</p>" );
}

# OK, we have data to process.
my $tmpfile_name = $q->tmpFileName( $tmpfile );

my $succ_msg = do_upload( csv_file => $tmpfile_name,
                          csv_name => $tmpfile );

my %tt_vars = (
                base_url => $base_url,
                succ_msg => $succ_msg,
              );
print $q->header;
$tt->process( "upload_breweries_complete.tt", \%tt_vars ) || die $tt->error;

# subroutines

sub do_upload {
  my %args = @_;
  my $csv_name = $args{csv_name};
  my $csv_file = $args{csv_file};

  my %data = PubSite->parse_breweries_csv( file => $csv_file );
  my @breweries = @{ $data{breweries} };

  my ( $min_lat, $max_lat, $min_long, $max_long )
    = @data{ qw( min_lat max_lat min_long max_long ) };

  my $index_url = $base_url . "breweries.html";
  my $map_url = $base_url . "breweries-map.html";
  my $tt_vars = {
                  base_url   => $base_url,
                  index_url  => $index_url,
                  map_url    => $map_url,
                  min_lat    => $min_lat,
                  max_lat    => $max_lat,
                  min_long   => $min_long,
                  max_long   => $max_long,
                  centre_lat => ( ( $max_lat + $min_lat ) / 2 ),
                  centre_long => ( ( $max_long + $min_long ) / 2 ),
                  updated => get_time(),
                  breweries  => \@breweries,
                };

  open( my $output_fh, ">", $base_dir . "breweries.html" )
    or print_form_and_exit( errmsg => $! );
  $tt->process( "breweries_index.tt", $tt_vars, $output_fh )
    or print_form_and_exit( errmsg => $tt->error );
  close $output_fh;

  open( my $output_fh, ">", $base_dir . "breweries-map.html" )
    or print_form_and_exit( errmsg => $! );
  $tt->process( "breweries_map.tt", $tt_vars, $output_fh )
    or print_form_and_exit( errmsg => $tt->error );
  close $output_fh;

  # If we get this far then hopefully we've succeeded.
  my $succ_msg = "Brewery data successfully uploaded. "
               . "<a href=\"$index_url\">Here is your index</a>, and "
               . "<a href=\"$map_url\">here is your map</a>.";
  return $succ_msg;
}

sub get_time {
  # strftime on here doesn't have %P
  return strftime( "%l:%M", localtime )
         . lc( strftime( "%p", localtime ) )
         . strftime( " on %A %e %B %Y", localtime );
}

sub print_form_and_exit {
  my %args = @_;

  my %tt_vars = (
                  base_url => $base_url,
                  cgi_url  => $cgi_url,
                  errmsg   => $args{errmsg} || "",
                );
  print $q->header;
  $tt->process( "upload_breweries_form.tt", \%tt_vars ) || die $tt->error;
  exit 0;
}
