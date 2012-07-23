use strict;
use Test::More;

plan tests => 12;

use_ok( "CGC", "Can use CGC.pm" );

my $may2012_text = qq(
Building society on [[Locale George Street|George Street]].

<div class="last_verified">Existence last checked in May 2012.</div>

<div class="neighbours">
<span>Church Street/Crown Hill/George Street</span>
...
\@THUMB [[Stan James Betting Shop, 8 Crown Hill|http://farm9.staticflickr.com/8012/7613748704_5457865a20_s_d.jpg]]
\@THUMB [[Barclays, 1 North End|http://farm8.staticflickr.com/7053/7002072804_f5549ecb85_s_d.jpg]]
\@THIS_THUMB [[Yorkshire Building Society, 3 George Street|http://farm8.staticflickr.com/7108/7474538170_e687e3744c_s_d.jpg]]
\@THUMB [[Stirfry's Chinese Buffet Restaurant, 3 George Street|http://farm9.staticflickr.com/8007/7474443622_399cac7edd_s_d.jpg]]
\@THUMB [[Allders, 2 North End|http://farm8.staticflickr.com/7274/7147998651_e62850d03a_s_d.jpg]]
...
</div>
);

my $may2012_text_long = qq(
Shoe repair place at the Crown Hill end of [[Locale Church Street|Church Street]].

As of July 2012, the frontage advertises shoe repairs, key cutting, engraving, watch repairs, sharpening, house signs, trophies, and chipped car keys.  However, on asking in the same month, the staff informed us that they do not in fact do knife sharpening.

Accessibility: A step to get in; because the shop is on a hill, this step is much taller at one side than at the other.

<div class="last_verified">Existence last checked in May 2012.</div>

<div class="neighbours">
<span>George Street/Crown Hill/Church Street</span>
...
\@THUMB [[Natwest, 1 High Street|http://farm9.staticflickr.com/8155/7121600299_17a66484c7_s_d.jpg]]
\@THUMB [[American Express Travel Services, 2-4 High Street|http://farm8.staticflickr.com/7263/7489691658_c704001bba_s_d.jpg]]
\@THIS_THUMB [[Shoe Care, 3 Crown Hill|http://farm9.staticflickr.com/8429/7609726636_6796721f98_s_d.jpg]]
\@THUMB [[Cotton County, 5 Crown Hill|http://farm9.staticflickr.com/8294/7609762456_23bef6fe10_s_d.jpg]]
\@THUMB [[7-9 Crown Hill|http://farm9.staticflickr.com/8433/7609757388_18251a1616_s_d.jpg]]
...
</div>
);

my $never_text = qq(
Building society on [[Locale George Street|George Street]].

<div class="neighbours">
<span>Church Street/Crown Hill/George Street</span>
...
\@THUMB [[Stan James Betting Shop, 8 Crown Hill|http://farm9.staticflickr.com/8012/7613748704_5457865a20_s_d.jpg]]
\@THUMB [[Barclays, 1 North End|http://farm8.staticflickr.com/7053/7002072804_f5549ecb85_s_d.jpg]]
\@THIS_THUMB [[Yorkshire Building Society, 3 George Street|http://farm8.staticflickr.com/7108/7474538170_e687e3744c_s_d.jpg]]
\@THUMB [[Stirfry's Chinese Buffet Restaurant, 3 George Street|http://farm9.staticflickr.com/8007/7474443622_399cac7edd_s_d.jpg]]
\@THUMB [[Allders, 2 North End|http://farm8.staticflickr.com/7274/7147998651_e62850d03a_s_d.jpg]]
...
</div>
);

my $date = CGC->extract_last_verified( $may2012_text );
is( $date, "May 2012", "extract_last_verified works for node with "
    . "free text, date div, and neighbours" );

$date = CGC->extract_last_verified( $may2012_text_long );
is( $date, "May 2012",
    "...also works for similar node with longer free text" );

$date = CGC->extract_last_verified( "something with no date" );
ok( !$date, "...and returns false for node with no divs" );

$date = CGC->extract_last_verified( $never_text );
ok( !$date,
    "...and returns false for node with neighbours but no last_verified" );

my $new_text = CGC->update_last_verified( text => $may2012_text,
                                          date => "August 2012" );
like( $new_text,
   qr|<div class="last_verified">Existence last checked in August 2012.</div>|,
   "update_last_verified works for node with free text, date div, and "
   . "neighbours" );

$new_text = CGC->update_last_verified( text => "something with no date",
                                       date => "August 2012" );
like( $new_text,
   qr|<div class="last_verified">Existence last checked in August 2012.</div>|,
   "...also works for node with no divs" );

$new_text = CGC->update_last_verified( text => $never_text,
                                       date => "August 2012" );
like( $new_text,
   qr|<div class="last_verified">Existence last checked in August 2012.</div>|,
   "...also works for node with neighbours but no last_verified");
like( $new_text,
      qr|<div class="last_verified">.*<div class="neighbours">|s,
      "...and gets the divs in the right order" );

my $n = CGC->months_since_last_verified( text => $may2012_text,
                                         date => "August 2012" );
is( $n, 3, "months_since_last_verified gives correct number of months for "
    . "node with free text, date div, and neighbours" );

$n = CGC->months_since_last_verified( text => "something with no date",
                                      date => "August 2012" );
is( $n, -1, "...and returns -1 for nodes with no divs" );

$n = CGC->months_since_last_verified( text => $never_text,
                                      date => "August 2012" );
is( $n, -1, "...and returns -1 for node with neighbours but no last_verified");
