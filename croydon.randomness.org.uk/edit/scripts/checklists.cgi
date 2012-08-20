#!/usr/bin/perl -w

use strict;

use lib qw(
    /export/home/rgc/web/vhosts/croydon.randomness.org.uk/scripts/lib/
    /export/home/rgc/perl5/lib/perl5/
);
use CGC;
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
my $split = $q->param( "split" );

my $format = $q->param( "format" ) || "";
if ( !$format || $format ne "print" ) {
  $format = "form";
}

if ( $format eq "form" ) {
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
    if ( $address !~ m/$number $locale/ || !$split ) {
      $type = "other";
    } elsif ( $number =~ /[13579][a-d]?$/ ) {
      $type = "odd";
    } else {
      $type = "even";
    }

    # Tweaks for individual addresses.
    if ( $address =~ /Norfolk House/ ) {
      $type = "odd" if $split;
    }
    if ( $name eq "Croydon Fruits And Vegetables, George Street" ) {
      $number = 95.5;
      $type = "odd" if $split;
    }
    if ( $name eq "Natwest, 1 High Street" && $locale eq "George Street" ) {
      $type = "even" if $split;
      $number = 0.5;
    }
    if ( $name eq "Allders, 2 North End" ) {
      $type = "odd" if $split;
      $number = 1;
    }
    if ( $name eq "East Croydon Station" ) {
      $type = "odd" if $split;
      $number = 99;
    }
    if ( $name eq "Spreadeagle, 39-41 Katharine Street"
         && $locale eq "High Street" ) {
      $type = "odd" if $split;
      $number = 43;
    }

    # London Road
    if ( $locale eq "London Road" ) {
      if ( $name eq "Molbee Motors, 1 Kidderminster Road" ) {
        $type = "even" if $split;
        $number = 180;
      }
      if ( $name eq "West Croydon Station" ) {
        $type = "even" if $split;
        $number = 8.9;
      }
      if ( $name eq "Road Runners, 174 North End" ) {
        $type = "even" if $split;
        $number = 8.8;
      }
      if ( $name eq "Sade's, 172 North End" ) {
        $type = "even" if $split;
        $number = 8.7;
      }
      if ( $name eq "Computer Repairs, 170 North End" ) {
        $type = "even" if $split;
        $number = 8.6;
      }
      if ( $name eq "H Purchen, 168 North End" ) {
        $type = "even" if $split;
        $number = 8.5;
      }
      if ( $name eq "Maplin, 166 North End" ) {
        $type = "even" if $split;
        $number = 8.4;
      }
      if ( $name eq "UCKG, 12-14 London Road" ) {
        $type = "even" if $split;
        $number = 15;
      }
      if ( $name eq "Zam Call, 181 North End" ) {
        $type = "odd" if $split;
        $number = 0.9;
      }
      if ( $name eq "Clearance Outlet, 177-179 North End" ) {
        $type = "odd" if $split;
        $number = 0.8;
      }
      if ( $name eq "175 North End" ) {
        $type = "odd" if $split;
        $number = 0.7;
      }
      if ( $name eq "Anadolu Kiraathanesi/Peri Community Centre, London Road" ) {
        $type = "odd" if $split;
        $number = 173;
      }
    }

    my $info = { name => $name,
                 address => $address,
                 number => $number,
                 type => $type };
    push @nodes, $info;
  }

  my @odds   = grep { $_->{type} eq "odd" }   @nodes;
  my @evens  = grep { $_->{type} eq "even" }  @nodes;
  my @others = grep { $_->{type} eq "other" } @nodes;
  @odds = sort { addr_sort( $a->{number}, $b->{number}, $dir ) } @odds;
  @evens = sort { addr_sort( $a->{number}, $b->{number}, $dir ) } @evens;
  @others = sort {$a->{address} cmp $b->{address} } @others;
  if ( !$split ) {
    @others = sort { addr_sort( $a->{number}, $b->{number}, $dir ) } @others;
  }

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

  $tt_vars{dir_box} = $q->radio_group(
      -name => "dir",
      -values => [ "asc", "desc" ],
      -labels => { asc => "ascending", desc => "descending" } );

  $tt_vars{split_box} = $q->checkbox(
      -name => "split", -value => 1, -label => "" );

  $tt_vars{format_box} = $q->radio_group(
      -name => "format",
      -values => [ "form", "print" ],
      -labels => { print => "printable", form => "interactive form" } );

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
  my $now = strftime( "%B %Y", localtime );

  # If it's already been verified this month, do nothing.
  my $last_checked = CGC->months_since_last_verified( text => $node{content},
                                                      date => $now );
#  return if $last_checked > -1 && $last_checked < 2;
  return unless $last_checked;

  my $new_content = CGC->update_last_verified( text => $node{content},
                                               date => $now );

  my %prefs = OpenGuides::CGI->get_prefs_from_cookie( config => $config );
  $node{metadata}{username} = $prefs{username};
  $node{metadata}{host} = $ENV{REMOTE_ADDR};
  $node{metadata}{edit_type} = "Minor tidying";
  $node{metadata}{major_change} = 0;
  $node{metadata}{comment} = "Updated last verified.";

  $wiki->write_node( $pagename, $new_content, $node{checksum},
                     $node{metadata} )
    or die "Can't write node!";
  return 1;
}

sub addr_sort {
  my ( $c, $d, $dir ) = @_;
  foreach ( ( $c, $d ) ) {
    s/^.*Woolwich House, //;
    s/^.*Grants Building, //;
    s/^.*The Arcade, //;
    s/^.*Boswell Cottage, //;
    s/11-12 Suffolk House,/70.11/;
    s/1-3 Suffolk House,/70.01/;
    s/1(\d)[a-d]? Suffolk House,/70.1$1/;
    s/(\d)[a-d]? Suffolk House,/70.0$1/;
    s/(\d+)[a-d]? Norfolk House,/69.$1/;
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
