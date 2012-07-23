package CGC;
use strict;

use DateTime::Format::Strptime;
use HTML::PullParser;

=head1 NAME

CGC - Utilities for the Completists' Guide to Croydon.

=head1 DESCRIPTION

Utilities for the Completists' Guide to Croydon.

=head1 METHODS

=over

=item B<extract_last_verified>

  my $date = CGC->extract_last_verified( $text );

Extract the "last verified" date from a node.  Returns a string like
"May 2012".

=cut

sub extract_last_verified {
  my ( $class, $text ) = @_;

  my $date = "";

  my $parser = HTML::PullParser->new( doc   => $text,
                                      start => '"START", tag, attr',
                                      end   => '"END", tag',
                                      text  => '"TEXT", text' );

  my $in_div;
  while ( my $token = $parser->get_token ) {
    my $flag = shift @$token;
    if ( $flag eq "START" ) {
      my ( $tag, $attr ) = @$token;
      if ( $tag eq "div" && $attr->{class} eq "last_verified" ) {
        $in_div = 1;
      }
    } elsif ( $flag eq "END" ) {
      my ($tag ) = @$token;
      if ( $tag eq "/div" && $in_div ) {
        last;
      }
    } elsif ( $flag eq "TEXT" && $in_div ) {
      $date .= shift @$token;
    }
  }

  return unless $date;
#warn "Date is $date\n";
  $date =~ s/Existence last checked in //;
  $date =~ s/\.$//;
  return $date;
}

=item B<update_last_verified>

  my $date = CGC->update_last_verified( text => $text, date => "May 2012" );

Update the "last verified" date in a node.  Returns the updated text
ready for writing to the node.  It updates the text even if the date
already in there is current, so you'll want to check on return whether
any changes have actually been made.

=cut

sub update_last_verified {
  my ( $class, %args ) = @_;
  my ( $text, $date ) = ( $args{text}, $args{date} );

  my $div = qq(<div class="last_verified">Existence last checked in)
             . " $date.</div>";
  my $re = qr/$div/;

  if ( $text !~ m|<div class="last_verified">| ) {
    if ( $text =~ m|<div class="neighbours">| ) {
      # Neighbour div but no last_verified div.
      $text =~ s|(<div class="neighbours">)|$div\n\n$1|;
    } else {
      # No neighbour div, no last_verified div.
      $text .= "\n\n$div";
    }
  } elsif ( $text !~ m/$re/ ) {
    # Already has a last_verified div.
    $text =~ s|<div class="last_verified">[^<]*</div>|$div|s;
  }

  return $text;
}

=item B<months_since_last_verified>

  my $n = CGC->months_since_last_verified( text => $text,
                                           date => "August 2012" );

Checks how many months it's been since the node was last verified.  If the
node has never been verified, returns -1.

=cut

sub months_since_last_verified {
  my ( $class, %args ) = @_;
  my $now = $args{date};
  my $then = $class->extract_last_verified( $args{text} );
#warn "N: $now, T: $then\n";
  return -1 unless $then;

  my $strp = DateTime::Format::Strptime->new(
    pattern => "%B %Y",
  );
  my $now_dt = $strp->parse_datetime( $now );
  my $then_dt = $strp->parse_datetime( $then );
#warn "About to get diff\n";
#warn "N: $now_dt, T: $then_dt\n";
  my $diff = $now_dt->delta_md( $then_dt );
#warn "About to get units\n";
  return $diff->in_units( "months" );
}

=back

=cut

return 1;
