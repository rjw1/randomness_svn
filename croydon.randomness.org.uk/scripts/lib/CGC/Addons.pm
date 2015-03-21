package CGC::Addons;

sub custom_macros {
    my ($class, %args ) = @_;
    my %macros = %{ $args{macros} };

    $macros{qr/\@INDEX_LIST\s+\[\[(Category|Locale)\s+([^\]]+)]]/}
      = sub {
        my ($wiki, $type, $value) = @_;
        unless ( UNIVERSAL::isa( $wiki, "Wiki::Toolkit" ) ) {
            return "(unprocessed INDEX_LIST macro)";
        }

        my @nodes = sort $wiki->list_nodes_by_metadata(
                       metadata_type  => $type,
                       metadata_value => $value,
                       ignore_case    => 1,
        );
        unless ( scalar @nodes ) {
            return qq(\n<div class="macro_index_list">)
                   . "\n* No pages currently in "
                   . lc($type) . " $value\n</div>";
        }

        # Split off address-only pages, and list them last.
        my @addr_only_nodes = sort { $class->cmp_addr( $a, $b ) }
                              grep( /^[-\d]+[ab]? /, @nodes );
        my %tmphash = map { $_ => 1 } @addr_only_nodes;
        my @occupied_nodes = grep( !$tmphash{$_}, @nodes );
                             

        my $return = qq(\n<div class="macro_index_list">\n);
        foreach my $node ( @occupied_nodes, @addr_only_nodes ) {
            if ( $node =~ /,/ ) {
                my $title = $node;
                my $address = $node;
                $address =~ s/^.*?, //;
                $title =~ s/, $address//;
                $return .= "* "
                    . $wiki->formatter->format_link( wiki => $wiki,
                                                     link => "$node|$title" )
                    . ", $address";
            } else {
                $return .= "* "
                    . $wiki->formatter->format_link( wiki => $wiki,
                                                     link => "$node" )
            }
            $return .= "\n";
	}
        $return .= "</div>";
        $return =~ s/%2C/,/gs;
        return $return;
    };

    $macros{qr/\@INDEX_ADDR_LIST\s+\[\[(Category|Locale)\s+([^\]]+)]]/}
      = sub {
        my ($wiki, $type, $value) = @_;
        unless ( UNIVERSAL::isa( $wiki, "Wiki::Toolkit" ) ) {
          return "(unprocessed INDEX_ADDR_LIST macro)";
        }

        my @nodes = $wiki->list_nodes_by_metadata(
                       metadata_type  => $type,
                       metadata_value => $value,
                       ignore_case    => 1 );
        unless ( scalar @nodes ) {
          return qq(\n<div class="macro_index_addr_list">)
                 . "\n* No pages currently in " . lc($type) . " $value\n"
                 . "</div>";
        }
        my $return = qq(\n<div class="macro_index_addr_list">\n);
        @nodes = sort { $class->cmp_addr( $a, $b ) } @nodes;
        foreach my $node ( @nodes ) {
            my ( $title, $address ) = split( /, /, $node );
            $return .= "* "
                    . $wiki->formatter->format_link( wiki => $wiki,
                                                     link => "$node|$title" );
            if ( $address ) {
                $return .= ", $address";
            }
            $return .= "\n";
        }
        $return .= "</div>";
        return $return;
    };

    $macros{qr/\@THUMB\s+\[\[([^|]+)\|([^]]+).*/}
      = sub {
        my ($wiki, $node, $image) = @_;
        return $class->do_thumb(wiki => $wiki, node => $node, image => $image);
    };

    $macros{qr/\@THUMB\s+\[\[([^|\]]+)\]\].*/}
      = sub {
        my ($wiki, $node) = @_;
        return $class->do_thumb( wiki => $wiki, node => $node );
    };

    $macros{qr/\@THIS_THUMB\s+\[\[([^|]+)\|([^]]+).*/}
      = sub {
        my ($wiki, $node, $image) = @_;
        return $class->do_thumb( wiki => $wiki, node => $node, image => $image,
                                this => 1 );
    };

    $macros{qr/\@THIS_THUMB\s+\[\[([^|\]]+)\]\].*/}
      = sub {
        my ($wiki, $node) = @_;
        return $class->do_thumb( wiki => $wiki, node => $node, this => 1 );
    };

    return %macros;
}

sub do_thumb {
    my $class = shift;
    my %args = @_;
    unless ( $args{wiki}
             && UNIVERSAL::isa( $args{wiki}, "Wiki::Toolkit" ) ) {
        return "(unprocessed THUMB macro)";
    }
    if ( $args{image} ) {
        $args{image} =~ s/<a href="//;
    } else {
        $args{image} = "http://croydon.randomness.org.uk/static/no-photo.png";
    }
    if ( $args{this} ) {
        return qq(<span class="this_thumb">)
               . qq(<img src="$args{image}" width="75" height="75" )
               . qq(alt="$args{node}" title="$args{node}" /></span>);
    } else {
        return qq(<span class="neighbour_thumb"><a href="wiki.cgi?)
               . $args{wiki}->formatter->node_name_to_node_param( $args{node} )
               . qq("><img src="$args{image}" width="75" height="75" )
               . qq(alt="$args{node}" title="$args{node}" /></a></span>);
    }
}

sub cmp_addr {
    my ( $class, $c, $d ) = @_;
    my %ad; my %bd;
    if ( $c =~ /,/ ) {
        ( $ad{name}, $ad{addr} ) = split( ",", $c );
    } else {
        $ad{name} = "";
        $ad{addr} = $c;
    }
    ( $ad{num}, $ad{street} ) = split( " ", $ad{addr} );

    if ( $d =~ /,/ ) {
        ( $bd{name}, $bd{addr} ) = split( ",", $d );
    } else {
        $bd{name} = "";
        $bd{addr} = $d;
    }
    ( $bd{num}, $bd{street} ) = split( " ", $bd{addr} );
    if ( $ad{street} ne $bd{street} ) {
        return $ad{street} cmp $bd{street};
    } elsif ( $ad{num} ne $bd{num} ) {
        return $ad{num} <=> $bd{num};
    }
    return $ad{name} cmp $bd{name};
}

1;
