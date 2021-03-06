#!/usr/bin/perl -w

use strict;

use lib qw(
    /export/home/rgc/web/vhosts/croydon.randomness.org.uk/scripts/lib/
    /export/home/rgc/perl5/lib/perl5/
);
use CGC;
use CGC::Routes;
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
my $umap = $q->param( "umap" ) || 0;
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

if ( $umap ) {
  my @streets = get_nodes_from_umap();
  $tt_vars{streets} = \@streets;
  output_and_exit( tt_vars => \%tt_vars );
} elsif ( scalar %wanted ) {
  my @streets = get_nodes_by_street();
  $tt_vars{streets} = \@streets;
  output_and_exit( tt_vars => \%tt_vars );
} else {
  # If we don't have anything to do, just print the form (if any) and message.
  output_and_exit( tt_vars => \%tt_vars );
}

sub output_and_exit {
  my %args = @_;
  my %tt_vars = %{ $args{tt_vars} || {} };

  my %prefs = OpenGuides::CGI->get_prefs_from_cookie( config => $config );
  $tt_vars{username} = $prefs{username};
  $tt_vars{cgi_url} = $q->url();

  $tt_vars{umap_box} = $q->checkbox(
      -name => "umap", -value => 1, -label => "" );

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
    if ( m/Norfolk House/ ) {
      s/(\d+)[a-d]? Norfolk House,/$1/;
      $_ /= 10;
    }
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

sub get_nodes_from_umap {
  # See surveys.cgi:
  my $json_url = "http://umap.openstreetmap.fr/en/datalayer/61278/";

  my @route = CGC::Routes->get_route_from_json_url( json_url => $json_url );
  my @to_survey = CGC::Routes->get_nodes_from_route(
                    guide => $guide, route => \@route );

  my @nodes = map { { name => $_, address => "dummy", number => -1,
                      type => "other" } } @to_survey;

  return ( { name => "from umap", odds => [], evens => [],
             others => \@nodes } );
}

sub get_nodes_by_street {
  my @locales = get_locales();

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

      # Church Street
      if ( $locale eq "Church Street" ) {
        if ( $name =~ /House Of Reeves/ ) {
          $type = "even" if $split;
          $number = 120;
        } elsif ( $name =~ /52 Tamworth Road/ ) {
          $type = "even" if $split;
          $number = 110;
        } elsif ( $name =~ /18 Crown Hill/ ) {
          $type = "even" if $split;
          $number = 14.9;
        } elsif ( $name =~ /20 Crown Hill/ ) {
          $type = "even" if $split;
          $number = 14.8;
        } elsif ( $name =~ /\s8 Crown Hill/ ) {
          $type = "even" if $split;
          $number = 14.7;
        } elsif ( $name =~ /1 North End/ ) {
          $type = "even" if $split;
          $number = 14.6;
        } elsif ( $name =~ /9 Crown Hill/ ) {
          $type = "odd" if $split;
          $number = 9.9;
        } elsif ( $name =~ /5 Crown Hill/ ) {
          $type = "odd" if $split;
          $number = 9.8;
        } elsif ( $name =~ /3 Crown Hill/ ) {
          $type = "odd" if $split;
          $number = 9.7;
        } elsif ( $name =~ /4 High Street/ ) {
          $type = "odd" if $split;
          $number = 9.6;
        }
      }

      # Derby Road
      if ( $locale eq "Derby Road" ) {
        if ( $name =~ /1 London Road/ ) {
          $type = "even" if $split;
          $number = 1;
        } elsif ( $name eq "Church Of God 7th Day Croydon, Derby Road" ) {
          $type = "odd" if $split;
          $number = 21;
        } elsif ( $name =~ /181a North End/ ) {
          $type = "odd" if $split;
          $number = 0.9;
        } elsif ( $name =~ /181 North End/ ) {
          $type = "odd" if $split;
          $number = 0.8;
        }
      }

      # Frith Road
      if ( $locale eq "Frith Road" ) {
        if ( $name =~ /78c Frith Road/ ) {
          $number = 78.3;
        } elsif ( $name =~ /78d Frith Road/ ) {
          $number = 78.4;
        }
      }

      # George Street
      if ( $locale eq "George Street" ) {
        if ( $name eq "East Croydon Station" ) {
          $type = "odd" if $split;
          $number = 99;
        } elsif ( $name =~ /4-5 Station Approach, George Street/ ) {
          $type = "odd" if $split;
          $number = 97.5;
        } elsif ( $name =~ /1-3 Station Approach, George Street/ ) {
          $type = "odd" if $split;
          $number = 97;
        } elsif ( $name eq "Croydon Fruits And Vegetables, George Street" ) {
          $type = "odd" if $split;
          $number = 95.5;
        } elsif ( $name eq "Natwest, 1 High Street" ) {
          $type = "even" if $split;
          $number = 0.5;
        } elsif ( $address =~ /Norfolk House/ ) {
          $type = "odd" if $split;
          $number += 37;
        } elsif ( $name =~ /, 2 North End/ ) {
          $type = "odd" if $split;
          $number = 1;
        }
      }

      # High Street
      if ( $locale eq "High Street" ) {
        if ( $name eq "Spreadeagle, 39-41 Katharine Street" ) {
          $type = "odd" if $split;
          $number = 43;
        }
        if ( $name eq "Tulsi ApartHotel, 256a High Street" ) {
          $number = 256.5;
        }
        if ( $name eq "Caprice, 108a High Street" ) {
          $number = 108.5;
        }
        if ( $name eq "Soulful Cellar, 90b High Street" ) {
          $number = 90.5;
        }
        if ( $name eq "Ponte Nuovo, 80-88 High Street" ) {
          $number = 88;
        }
        if ( $name eq "Caffe Del Ponte, 80-88 High Street" ) {
          $number = 80;
        }
        if ( $name eq "Streeter Marshall, 78a High Street" ) {
          $number = 78.5;
        }
        if ( $name eq "Quick Stop Food And Wine, 76a High Street" ) {
          $number = 76.5;
        }
        if ( $name eq "Petit Cafe, 74a High Street" ) {
          $number = 74.5;
        }
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
        if ( $name =~ m/179 North End$/ ) {
          $type = "odd" if $split;
          $number = 0.8;
        }
        if ( $name =~ m/175 North End$/ ) {
          $type = "odd" if $split;
          $number = 0.7;
        }
        if ( $name eq
                   "Anadolu Kiraathanesi/Peri Community Centre, London Road" ) {
          $type = "odd" if $split;
          $number = 173;
        }
      }

      # North End
      if ( $locale eq "North End" ) {
        # West side
        if ( $name =~ /135a North End/ ) {
          $number = 133.5;
        } elsif ( $name =~ /139a North End/ ) {
          $number = 137.5;
        } elsif ( $name eq "Zara, Centrale" ) {
          $type = "odd" if $split;
          $number = 113;
        } elsif ( $name eq "Aldo, Centrale" ) {
          $type = "odd" if $split;
          $number = 111;
        } elsif ( $name eq "Next, Centrale" ) {
          $type = "odd" if $split;
          $number = 109;
        } elsif ( $name eq "Rush Advanced Academy, 73 North End" ) {
          $number = 73.5;
        } elsif ( $name =~ /Poundworld, Centrale/ ) {
          $type = "odd" if $split;
          $number = 47;
        } elsif ( $name eq "Metro Bank, Centrale" ) {
          $type = "odd" if $split;
          $number = 45;
        } elsif ( $name eq "Reggaemasters, 1 Drummond Road" ) {
          $type = "odd" if $split;
          $number = 69.5;
        }
        # East side
        elsif ( $name =~ /30-32 North End/ ) {
          $number = 32;
        } elsif ( $name =~ /34-36 North End/ ) {
          $number = 36.5;
        }
      }

      # Selsdon Road
      if ( $locale eq "Selsdon Road" ) {
        if ( $name =~ /1a Selsdon Road/ ) {
          $number = 0.1;
        } elsif ( $name =~ /1b Selsdon Road/ ) {
          $number = 0.2;
        } elsif ( $name =~ /William Hill, 1 Selsdon Road/ ) {
          $number = 0.3;
        } elsif ( $name =~ /20e Selsdon Road/ ) {
          $number = 20.5;
        } elsif ( $name =~ /20d Selsdon Road/ ) {
          $number = 20.4;
        } elsif ( $name =~ /20c Selsdon Road/ ) {
          $number = 20.3;
        } elsif ( $name =~ /20a-20b Selsdon Road/ ) {
          $number = 20.2;
        } elsif ( $name =~ /18c Selsdon Road/ ) {
          $number = 18.5;
        } elsif ( $name =~ /12a Selsdon Road/ ) {
          $number = 11.5;
        } elsif ( $name =~ /2a Selsdon Road/ ) {
          $number = 1.5;
        } elsif ( $name =~ /1 Croham Road/ ) {
          $type = "odd" if $split;
          $number = 16.99;
        } elsif ( $name =~ /1 Brighton Road/ ) {
          $type = "even" if $split;
          $number = 0.1;
        }
        if ( $name =~ /(\d+) Ye Market/ ) {
          $type = "odd" if $split;
          $number = 16 + 0.01 * $1;
        }
        if ( $name =~ /(\d)(-\d)? Ruskin Parade/ ) {
          $type = "odd" if $split;
          $number = 11 + 0.1 * $1;
        }
        if ( $name =~ /South End/ ) {
          next;
        }
      }

      # South End
      if ( $locale eq "South End" ) {
        if ( $name eq "Croydon Jewellery School, 22 South End" ) {
          $number = 22;
        }
        if ( $name eq "Scream Studios, 20a South End" ) {
          $number = 20.5;
        }
        if ( $name =~ /38a South End/ ) {
          $number = 36.5;
        }
        if ( $name eq "Jacksons Property Services, 82-84 South End" ) {
          $number = 84;
        }
        if ( $name eq "MSC/Modern Sports Classics (CLOSED), 96b South End" ) {
          $number = 96.1;
        }
        if ( $name eq "Keepers, 96a South End" ) {
          $number = 96.2;
        }
        if ( $name eq "Sovereign Cars, 96a South End" ) {
          $number = 96.3;
        }
        if ( $name eq "Kwintessential, 96d South End" ) {
          $number = 96.4;
        }
        if ( $name eq "Croydon Cosmetic Clinic, 98a South End" ) {
          $number = 98.5;
        }
        if ( $name =~ /1 Brighton Road/ ) {
          $type = "even" if $split;
          $number = 106;
        }
      }

      # Station Road
      if ( $locale eq "Station Road" ) {
        if ( $address =~ /18b Station Road/ ) {
          $number = 18.5;
        }
      }

      # St George's Walk
      if ( $locale eq "St George's Walk" ) {
        if ( $address =~ /23-25 High Street/ ) {
          $type = "odd" if $split;
          $number = 1;
        } elsif ( $address =~ /27 High Street/ ) {
          $type = "even" if $split;
          $number = 1;
        } elsif ( $address =~ /41a St George's Walk/ ) {
          $number = 41.5;
        } elsif ( $address =~ /26a St George's Walk/ ) {
          $number = 26.5;
        }
      }

      # Wellesley Road
      if ( $locale eq "Wellesley Road" ) {
        if ( $address =~ /Norfolk House/ ) {
          $type = "even" if $split;
          if ( $name =~ /Travelodge/ ) {
            # Divide by 10 as above to force Norfolk House south of Office Angels
            $number = 0.9;
          }
        } elsif ( $address =~ /43 George Street/ ) {
          $type = "odd" if $split;
          $number = 11;
        } elsif ( $address =~ /66-68 George Street/ ) {
          $type = "odd" if $split;
          $number = 13;
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
  return @streets;
}
