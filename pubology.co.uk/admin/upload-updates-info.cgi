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
$tt->process( "upload_updates_info_complete.tt", \%tt_vars ) || die $tt->error;

# subroutines

sub do_upload {
  my %args = @_;
  my $csv_name = $args{csv_name};
  my $csv_file = $args{csv_file};

  my @updates = PubSite->parse_updates_info_csv(
    file          => $csv_file,
  );
  @updates = reverse @updates;

  my $tt_vars = {
                  base_url => $base_url,
                  updates  => \@updates,
                };

  open( my $output_fh, ">", $base_dir . "updates.html" )
    or print_form_and_exit( errmsg => $! );
  $tt->process( "updates.tt", $tt_vars, $output_fh )
    or print_form_and_exit( errmsg => $tt->error );
  close $output_fh;

  # If we get this far then hopefully we've succeeded.
  my $succ_msg = "Data on updates successfully uploaded.";
  return $succ_msg;
}

sub print_form_and_exit {
  my %args = @_;

  my %tt_vars = (
                  base_url => $base_url,
                  cgi_url  => $cgi_url,
                  errmsg   => $args{errmsg} || "",
                );
  print $q->header;
  $tt->process( "upload_updates_info_form.tt", \%tt_vars ) || die $tt->error;
  exit 0;
}
