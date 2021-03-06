#!/usr/bin/perl

use strict;
use warnings;

use lib qw(
            /export/home/rgc/perl5/lib/perl5/
            /export/home/rgc/web/vhosts/croydon.randomness.org.uk/scripts/lib/
);
use CGI;
use OpenGuides;
use OpenGuides::CGI;
use OpenGuides::Config;
use POSIX qw( strftime );
use Template;

my $config_file = $ENV{OPENGUIDES_CONFIG_FILE} || "../wiki.conf";
my $config = OpenGuides::Config->new( file => $config_file );
my $guide = OpenGuides->new( config => $config );
my $wiki = $guide->wiki;
my $formatter = $wiki->formatter;
my $q = CGI->new;
my @locales = get_locales();
my %tt_vars;

# Find out what to do.
my %wanted = map { lc( $_ ) => 1 } $q->param( "street" );
my $dir = $q->param( "dir" );
if ( !$dir || $dir ne "desc" ) {
  $dir = "asc";
}

my $format = $q->param( "format" ) || "";
if ( $format ne "print" ) {
  $tt_vars{streets_box} = make_streets_box();
  # Only one street at a time if we're not doing the printable version.
  my @streets = sort keys %wanted;
  %wanted = ( $streets[0] => 1 );
}

my $action = $q->param( "action" ) || "";
if ( $action eq "update" ) {
  update_and_exit( tt_vars => \%tt_vars );
}

# If we don't have anything to do, just print the form (if any) and a message.
if ( !scalar %wanted ) {
  output_and_exit( tt_vars => \%tt_vars );
}

# Process the locales one at a time.
my @streets;
foreach my $locale ( sort @locales ) {
  next unless $wanted{ lc( $locale ) };
  my @names = $wiki->list_nodes_by_metadata(
                  metadata_type => "locale",
                  metadata_value => $locale,
                  ignore_case => 1 );
  my @nodes;
  foreach my $name ( @names ) {
    my %data = $wiki->retrieve_node( $name );
    my $type;
    my $address = $data{metadata}{address}[0];
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
  @odds = sort { addr_sort( $a->{number}, $b->{number}, $dir ) } @odds;
  @evens = sort { addr_sort( $a->{number}, $b->{number}, $dir ) } @evens;
  @others = sort {$a->{address} cmp $b->{address} } @others;

  push @streets, { name => $locale, odds => \@odds, evens => \@evens,
                   others => \@others };
}

$tt_vars{streets} = \@streets;
output_and_exit( tt_vars => \%tt_vars );

sub output_and_exit {
  my %args = @_;
  my %tt_vars = %{ $args{tt_vars} || {} };

  my %prefs = OpenGuides::CGI->get_prefs_from_cookie( config => $config );
  $tt_vars{username} = $prefs{username};
  $tt_vars{cgi_url} = $q->url();

  my $custom_template_path = $config->custom_template_path || "";
  my $template_path = $config->template_path;
  my $tt = Template->new( {
               INCLUDE_PATH => ".:$custom_template_path:$template_path" } );
  print $q->header;
  my $template = ( $format eq "print" ) ? "lists_printable.tt" : "lists.tt";
  $tt->process( $template, \%tt_vars );
  exit 0;
}

sub update_and_exit {
  my %args = @_;
  my %tt_vars = %{ $args{tt_vars} || {} };

  my @to_update = $q->param( "update_last_verified" );

  my ( @non_existent, @not_updated, @updated );
  foreach my $node ( sort @to_update ) {
    if ( !page_exists( $node ) ) {
      push @non_existent, $node;
    } else {
      if ( update_last_verified( $node ) ) {
        push @updated, $node;
      } else {
        push @not_updated, $node;
      }
    }
  }

  $tt_vars{did_update} = 1;
  $tt_vars{non_existent} = \@non_existent;
  $tt_vars{updated} = \@updated;
  $tt_vars{not_updated} = \@not_updated;

  output_and_exit( tt_vars => \%tt_vars );
}

sub update_last_verified {
  my $pagename = shift;
  my %node = $wiki->retrieve_node( $pagename );
  my $to_edit;
  my $monthyear = strftime( "%B %Y", localtime );
  my $div = qq(<div class="last_verified">Existence last checked in)
             . " $monthyear.</div>";
  my $re = qr/$div/;

  my $content = $node{content};
  if ( $content !~ m|<div class="last_verified"| ) {
    $content .= "\n\n$div";
    $to_edit = 1;
  } elsif ( $content !~ m/$re/ ) {
    $content =~ s|<div class="last_verified">[^<]*</div>|$div|s;
    $to_edit = 1;
  }

  return unless $to_edit;

  my %prefs = OpenGuides::CGI->get_prefs_from_cookie( config => $config );
  $node{metadata}{username} = $prefs{username};
  $node{metadata}{host} = $ENV{REMOTE_ADDR};
  $node{metadata}{edit_type} = "Minor tidying";
  $node{metadata}{major_change} = 0;
  $node{metadata}{comment} = "Updated last verified.";

  $wiki->write_node( $pagename, $content, $node{checksum}, $node{metadata} )
    or die "Can't write node!";
  return 1;
}

sub addr_sort {
  my ( $c, $d, $dir ) = @_;
  foreach ( ( $c, $d ) ) {
    s/-.*$//;
    s/[a-d]$//;
  }
  if ( $dir eq "asc" ) {
    return $c <=> $d;
  } else {
    return $d <=> $c;
  }
}

sub make_streets_box {
  my @locales = get_locales();
  my %labels = map { lc( $_ ) => $_ } @locales;
  my @values = sort keys %labels;
  return $q->popup_menu(
    -name => "street",
    -values => [ "", @values ],
    -labels => { "" => "-- choose --", %labels },
  );
}

sub get_locales {
  if ( scalar @locales ) {
    return @locales;
  }
  my @nodes = $wiki->list_nodes_by_metadata(
                metadata_type => "category",
                metadata_value => "locales",
                ignore_case => 1 );
  my %locs = map { s/Locale //; $_ => 1 } @nodes;
  delete $locs{Croydon};
  return keys %locs;
}

sub page_exists {
  my $pagename = shift;
  return $wiki->node_exists( $pagename );
}
