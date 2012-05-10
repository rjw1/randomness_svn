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
use OpenGuides::CGI;
use OpenGuides::Config;
use POSIX qw( strftime );
use Template;
use URI::Encode qw( uri_encode );
use WWW::Mechanize;

my $config_file = $ENV{OPENGUIDES_CONFIG_FILE} || "../wiki.conf";
my $config = OpenGuides::Config->new( file => $config_file );
my $guide = OpenGuides->new( config => $config );
my $wiki = $guide->wiki;
my $formatter = $wiki->formatter;
my $base_url = $config->script_url . $config->script_name;
my $new_page_url = $config->script_url . "newpage.cgi";
# Turn autocheck off since we check page existence by seeing if we get a
# failure on trying to view it.
my $agent = WWW::Mechanize->new( autocheck => 0 );
$agent->credentials( "croydon", "rocks" );
my $q = CGI->new;
my %locales = get_locales();
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
foreach my $locale ( sort keys %locales ) {
  next unless $wanted{ lc( $locale ) };
  my $url = "$base_url?action=index;loc=" . uri_encode( $locale )
            . ";format=json";
  my @nodes;
  $agent->get( $url );
  my $json = $agent->content;
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
  $agent->get( $new_page_url );
  $agent->submit_form( form_number => 2,
                       fields => { pagename => $pagename } );
  my $to_edit;
  my $monthyear = strftime( "%B %Y", localtime );
  my $div = qq(<div class="last_verified">Existence last checked in)
             . " $monthyear.</div>";
  my $re = qr/$div/;

  my $content = $agent->value( "content" );
  if ( $content !~ m|<div class="last_verified"| ) {
    $content .= "\n\n$div";
    $to_edit = 1;
  } elsif ( $content !~ m/$re/ ) {
    $content =~ s|<div class="last_verified">[^<]*</div>|$div|s;
    $to_edit = 1;
  }  

  return unless $to_edit;

  my %prefs = OpenGuides::CGI->get_prefs_from_cookie( config => $config );
  my $username = $prefs{username};

  # Hack around bug in WWW::Mechanize.
  my $locales = $agent->value( "locales" );
  $locales =~ s/\n/\r\n/gs;
  my $categories = $agent->value( "categories" );
  $categories =~ s/\n/\r\n/gs;
  $agent->submit_form( form_number => 1,
                       fields => {
                                   locales => $locales,
                                   categories => $categories,
                                   content => $content,
                                   username => $username,
                                   comment => "Updated last verified.",
                                   edit_type => "Minor tidying",
                                 }, 
                       button => "Save", 
                     );
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
  my %locales = get_locales();
  my %labels = map { lc( $_ ) => $_ } keys %locales;
  my @values = sort keys %labels;
  return $q->popup_menu(
    -name => "street",
    -values => [ "", @values ],
    -labels => { "" => "-- choose --", %labels },
  );
}

sub get_locales {
  if ( scalar %locales ) {
    return %locales;
  }
  my $url = "$base_url?action=index;cat=locales;format=json";
  $agent->get( $url );
  my $json = $agent->content;
  my $locale_data = decode_json( $json );
  my %locales = map { my $name = $_->{name}; $name =~ s/^Locale //;
                      $name => $_->{param} } @$locale_data;
  delete $locales{Croydon};
  return %locales;
}

sub page_exists {
  my $pagename = shift;
  $agent->get( $new_page_url );
  $agent->submit_form( form_number => 2,
                       fields => { pagename => $pagename } );
  $agent->follow_link( text => "cancel edit" );
  $agent->follow_link( text => "Cancel edit" );
  my $html = $agent->content();
  if ( $html =~ /We don't have a (page|node) called/ ) {
    return 0;
  }
  return 1;
}
