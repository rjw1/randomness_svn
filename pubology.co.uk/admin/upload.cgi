#!/usr/bin/perl -w

use strict;

use lib qw(
            /export/home/pubology/lib/
            /export/home/pubology/perl5/lib/perl5/
          );

use CGI;
use CGI::Carp qw( fatalsToBrowser );
use Config::Tiny;
use POSIX qw( strftime );
use PubSite;
use Template;

my $HOME = "/export/home/pubology";
my $base_dir = "$HOME/web/vhosts/pubology.co.uk/";
my $base_url = "http://www.pubology.co.uk/";

my %regexes = (
      "central london"    => qr/^[EW]C\d/i,
      "east london"       => qr/^E\d/i,
      "north london"      => qr/^N\d/i,
      "north-west london" => qr/^NW\d/i,
      "outer london"      => qr/^[BCHTU][ABRW]\d/i,
      "south-west london" => qr/^SW\d/i,
      "south-east london" => qr/^SE\d/i,
      "west london"       => qr/^W\d/i,
);

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
my %tt_base_vars = ( base_url => $base_url );

# If we aren't trying to upload, just print the form.
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

my $succ_msg = do_upload( csv_file => $tmpfile_name, csv_name => $tmpfile );

my %tt_vars = (
                cgi_url => $cgi_url,
                base_url => $base_url,
                succ_msg => $succ_msg,
              );
print $q->header;
$tt->process( "upload_complete.tt", \%tt_vars ) || die $tt->error;

# subroutines

sub do_upload {
  my %args = @_;
  my $csv_name = $args{csv_name};
  my $csv_file = $args{csv_file};

  # Check we can extract the postal district.
  my $postal_district = lc( $csv_name );
  $postal_district =~ s/^pubs //;
  $postal_district =~ s/\.csv$//;

  if ( $postal_district !~ m/^[bcdehiknrstuw][abcdegmnprtw]?\d\d?[cw]?$/i ) {
    print_form_and_exit( errmsg => "<p>Filename '$csv_name' in wrong format "
      . "&#8212; should be of the form 'Pubs [postal district].csv', where "
      . "postal district is one or two letters followed by one or two "
      . "numbers and an optional final letter.</p>" );
  }

  # Check postal district is valid and figure out which area it's in.
  my $district_conf = PubSite->parse_postal_district_config(
                          file => "$HOME/conf/postal_districts.conf",
    ) || print_form_and_exit( errmsg => "<p>$PubSite::errstr</p>" );

  my $this_area;
  foreach my $area ( keys %regexes ) {
    if ( $postal_district =~ $regexes{$area} ) {
      $this_area = $area;
      last;
    }
  }

  if ( !$this_area ) {
    print_form_and_exit( errmsg => "<p>Couldn't match postal district \""
              . $q->escapeHTML( $postal_district ) . "\" to an area of "
              . "London.  If you're sure the postal district is correct, "
              . "please report this as a bug.</p>" );
  } elsif ( !$district_conf->{lc($this_area)} ) {
    print_form_and_exit( errmsg => "<p>Couldn't find config information for "
              . "postal district "
              . $q->escapeHTML( $postal_district ) . " &#8212; please report "
              . "this as a bug.</p>" );
  }

  my $config = Config::Tiny->read( "$HOME/conf/pubology.conf" )
                 or croak "Can't read config file: $Config::Tiny::errstr "
                        . "(please report this as a bug)";

  my $flickr_key    = $config->{_}->{flickr_key}    || "";
  my $flickr_secret = $config->{_}->{flickr_secret} || "";

  my %data = PubSite->parse_csv(
    file          => $csv_file,
    check_flickr  => 1,
    flickr_key    => $flickr_key,
    flickr_secret => $flickr_secret,
  );
  my @pubs = @{ $data{pubs} };

  my ( $min_lat, $max_lat, $min_long, $max_long )
    = @data{ qw( min_lat max_lat min_long max_long ) };

  my $map_file = "maps/" . lc( $postal_district ) . ".html";
  my $map_url = $base_url . $map_file;
  my $district_file = "indexes/" . lc( $postal_district ) . ".html";
  my $district_url = $base_url . $district_file;
  my $kml_file = "kml/" . lc( $postal_district ) . ".kml";
  my $kml_url = $base_url . $kml_file;

  foreach my $pub ( @pubs ) {
    write_pub_page( pub => $pub, map_url => $map_url,
                    district_url => $district_url,
                    postal_district => $postal_district );
  }

  write_map_page( this_area => $this_area, pubs => \@pubs,
    district_url => $district_url, min_lat => $min_lat, max_lat => $max_lat,
    min_long => $min_long, max_long => $max_long,
    postal_district => $postal_district, map_file => $map_file );

  write_district_page( district_file => $district_file, pubs => \@pubs,
      postal_district => $postal_district, map_url => $map_url );

  write_kml_file( pubs => \@pubs, postal_district => $postal_district,
      kml_file => $kml_file );

  rewrite_index( this_area => $this_area, district_conf => $district_conf );

  # If we get this far then hopefully we've succeeded.
  my $succ_msg = "Data successfully uploaded for " . uc( $postal_district )
               . ". "
               . "<a href=\"$base_url$district_file\">Here is your index</a>, "
               . "<a href=\"$base_url$map_file\">here is your map</a>, and "
               . "<a href=\"$base_url$kml_file\">here is your KML</a>.";
  return $succ_msg;
}

sub write_pub_page {
  my %args = @_;
  my $tt_vars = { %args, %tt_base_vars };
  my $template = "pub_page.tt";

  open( my $output_fh, ">", "$base_dir/pubs/" . $args{pub}{id} . ".html" )
      or die $!;
  $tt->process( $template, $tt_vars, $output_fh )
    || print_form_and_exit( errmsg => $tt->error );
}

sub get_time {
  # strftime on here doesn't have %P
  return strftime( "%l:%M", localtime )
         . lc( strftime( "%p", localtime ) )
         . strftime( " on %A %e %B %Y", localtime );
}

sub write_map_page {
  my %args = @_;

  my $area_name = $args{this_area};
  $area_name =~ s/\b(\w)/\u$1/g;
  my $area_file = $args{this_area};
  $area_file =~ s/\s+/-/g;

  $args{postal_district} = uc( $args{postal_district} );
  my $tt_vars = {
    %tt_base_vars,
    %args,
    area_name => $area_name,
    area_file => $area_file,
    centre_lat => ( ( $args{max_lat} + $args{min_lat} ) / 2 ),
    centre_long => ( ( $args{max_long} + $args{min_long} ) / 2 ),
    updated => get_time(),
  };

  my $template = "map.tt";
  open( my $output_fh, ">", $base_dir . $args{map_file} ) or die $!;
  $tt->process( $template, $tt_vars, $output_fh )
    || print_form_and_exit( errmsg => $tt->error );
}

sub write_district_page {
  my %args = @_;

  $args{postal_district} = uc( $args{postal_district} );

  my $tt_vars = {
    %tt_base_vars,
    %args,
    updated => get_time(),
  };

  my $template = "district_index.tt";
  open( my $output_fh, ">", $base_dir . $args{district_file} ) or die $!;
  $tt->process( $template, $tt_vars, $output_fh )
    || print_form_and_exit( errmsg => $tt->error );
}

sub write_kml_file {
  my %args = @_;
  my @pubs = @{$args{pubs}};

  my @points;
  foreach my $pub ( @pubs ) {
    if ( !$pub->lat || !$pub->long ) {
      next;
    }
    my %data = (
                 name => $pub->name,
                 long => $pub->long,
                 lat => $pub->lat,
                 address => $pub->address,
                 url => $base_url . "pubs/" . $pub->id . ".html",
               );
    if ( $pub->demolished ) {
      $data{style} = "red";
    } elsif ( $pub->closed ) {
      $data{style} = "yellow";
    } else {
      $data{style} = "green";
    }
    push @points, \%data;
  }

  my $tt_vars = {
    %tt_base_vars,
    points => \@points,
    postal_district => uc( $args{postal_district} ),
  };

  my $template = "kml.tt";
  open( my $output_fh, ">", $base_dir . $args{kml_file} ) or die $!;
  $tt->process( $template, $tt_vars, $output_fh )
    || print_form_and_exit( errmsg => $tt->error );
}

sub rewrite_index {
  my %args = @_;
  my $area = $args{this_area};
  my $district_conf = $args{district_conf};

  # already checked this exists in the config
  my %district_names = %{ $district_conf->{ lc( $area ) } };

  opendir( my $dh, $base_dir . "indexes" ) || croak "Can't open $base_dir";
  my @files = grep { /\.html$/ } readdir( $dh );
  @files = grep { $regexes{ $area } } @files;
  my %urls = map { my $label = $_;
                   $label =~ s/\.html//;
                   { uc( $label ) => $base_url . "indexes/$_" }
                 } @files;

  my @all_districts = map { my $label = uc( $_ );
                            {
                              label => $label,
                              url   => $urls{$label} || "",
                              name  => $district_names{$label}
                            }
                          } sort { pc_cmp( $a, $b ) } keys %district_names;

  my @district_sets;
  my $divisions = $district_conf->{ lc( "$area divisions" ) } || 0;
  if ( $divisions ) {
    my %div_hash = %$divisions;
    foreach my $name ( sort keys %div_hash ) {
      my $district_str = $div_hash{$name};
      my @districts = split /\s*,\s*/, $district_str;
      my %dist_hash = map { $_ => 1 } @districts;
      my @these_districts = grep { $dist_hash{$_->{label}} } @all_districts;
      push @district_sets, {
        name => $name,
        districts => \@these_districts,
      };
    }
  } else {
    @district_sets = ( { districts => \@all_districts } );
  }

  my $area_name = $area;
  $area_name =~ s/\b(\w)/\u$1/g;
  my $area_file = $area;
  $area_file =~ s/\s+/-/g;

  my $tt_vars = {
                  %tt_base_vars,
                  area_name => $area_name,
                  district_sets => \@district_sets,
                };

  open( my $output_fh, ">", $base_dir . "indexes/$area_file.html" )
    or print_form_and_exit( errmsg => $! );
  $tt->process( "area_index.tt", $tt_vars, $output_fh )
    or print_form_and_exit( errmsg => $tt->error );
}

sub pc_cmp {
  my ( $pc1a, $pc1b, $pc1c, $pc2a, $pc2b, $pc2c );
  $pc1c = $pc1b = $pc1a = shift;
  $pc2c = $pc2b = $pc2a = shift;

  if ( $pc1c =~ m/^[A-Z]+\d+([A-Z]+$)/ ) {
    $pc1c = $1;
    $pc1a =~ s/^([A-Z]+\d+)[A-Z]+$/$1/;
  } else {
    $pc1c = "";
  }

  if ( $pc2c =~ m/^[A-Z]+\d+([A-Z]+$)/ ) {
    $pc2c = $1;
    $pc2a =~ s/^([A-Z]+\d+)[A-Z]+$/$1/;
  } else {
    $pc2c = "";
  }

  $pc1a =~ s/\d//g;
  $pc2a =~ s/\d//g;
  $pc1b =~ s/[A-Z]//g;
  $pc2b =~ s/[A-Z]//g;

  if ( $pc1a ne $pc2a ) {
    return $pc1a cmp $pc2a;
  }

  if ( $pc1b != $pc2b ) {
    return $pc1b <=> $pc2b;
  }

  if ( $pc1c && $pc2c ) {
    return $pc1c cmp $pc2c;
  }

  if ( $pc1c ) {
    return 1;
  }

  if ( $pc2c ) {
    return -1;
  }

  return 0;
}

sub print_form_and_exit {
  my %args = @_;

  my %tt_vars = (
                  cgi_url => $cgi_url,
                  base_url => $base_url,
                  postal_district_field =>
                                  $q->textfield( -name => "postal_district" ),
                  errmsg => $args{errmsg} || "",
                );
  print $q->header;
  $tt->process( "upload_form.tt", \%tt_vars ) || die $tt->error;
  exit 0;
}
