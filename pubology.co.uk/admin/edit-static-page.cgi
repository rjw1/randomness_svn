#!/usr/bin/perl -w

use strict;

use lib qw(
            /export/home/pubology/lib/
            /export/home/pubology/perl5/lib/perl5/
          );

use CGI;
use CGI::Carp qw( fatalsToBrowser );
use HTML::Entities;
use HTML::PullParser;
use HTML::TokeParser;
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

my $errmsg;

# Types of page we can edit.
my $page = $q->param( "page" ) || "";
if ( $page ne "front" && $page ne "updates" && $page ne "notes" ) {
  print $q->redirect( $base_url . "admin/index.cgi" );
  exit 0;
}
my ( $page_file, $template_file, $div_id, $text );
if ( $page eq "front" ) {
  $page_file = $base_dir . "index.html";
  $template_file = "index.tt";
  $div_id = "front_page_text";
  $text = $q->param( "front_page_text" );
} elsif ( $page eq "updates" ) {
  $page_file = $base_dir . "updates.html";
  $template_file = "updates.tt";
  $div_id = "updates_page_text";
  $text = $q->param( "updates_page_text" );
} else {
  $page_file = $base_dir . "notes.html";
  $template_file = "notes.tt";
  $div_id = "notes_page_text";
  $text = $q->param( "notes_page_text" );
}

if ( $q->param( "Save" ) ) {
  if ( !$text ) {
    $errmsg = "<p>Must supply some text.</p>";
  }
}

if ( $errmsg || !$q->param( "Save" ) ) {
  print_form_and_exit( errmsg => $errmsg, page_file => $page_file,
                       div_id => $div_id, page => $page );
}

write_static_page( text => $text, page_file => $page_file,
                   template_file => $template_file );

my %tt_vars = (
                base_url => $base_url,
                cgi_url => $cgi_url,
                page => $page,
              );
print $q->header;
$tt->process( "static_page_edited.tt", \%tt_vars ) || croak $tt->error;

sub write_static_page {
  my %args = @_;
  my $text = $args{text};
  my $page_file = $args{page_file};
  my $template_file = $args{template_file};
  my $encoded_text = "";

  # deal with line breaks
#  $text =~ s|\r\n|<br>|g;

  # PullParser rather than TokeParser because it seems a simpler way of doing
  # it here.  I think?  This may be an artefact of me having previously done
  # it this way in Wiki::Toolkit though.
  my $parser = HTML::PullParser->new(
                                      doc => $text,
                                      start => '"TAG", tag, text',
                                      end   => '"TAG", tag, text',
                                      text  => '"TEXT", tag, text'
                                    );

  my %allowed = map { lc($_) => 1, "/" . lc($_) => 1 }
                qw( b i strong em a br ul li hr h3 h4 h5 h6 p );
  while ( my $token = $parser->get_token ) {
    my ( $flag, $tag, $stuff, $attr ) = @$token;
    if ( $flag eq "TAG" and !defined $allowed{ lc( $tag ) } ) {
      $encoded_text .= encode_entities( $stuff );
    } else {
      $encoded_text .= $stuff;
    }
  }

  my $tt_vars = { text => $encoded_text };
  open( my $output_fh, ">", $page_file )
    || print_form_and_exit( errmsg => $! );
  $tt->process( $template_file, $tt_vars, $output_fh )
    || print_form_and_exit( errmsg => $tt->error );
}

sub print_form_and_exit {
  my %args = @_;

  open( my $fh, "<", $args{page_file} )
    || die $!;
  my $parser = HTML::TokeParser->new( $fh );

  my $current_text = "";
  while ( my $token = $parser->get_tag( "div" ) ) {
    my $attrs = $token->[1];
    if ( $attrs->{id} eq $args{div_id} ) {
      while ( my $bit = $parser->get_token ) {
        if ( $bit->[0] eq "E" && $bit->[1] eq "div" ) {
          last;
        }
        if ( $bit->[0] eq "S" ) {
          if ( $bit->[1] eq "a" ) {
            my $href = $bit->[2]->{href};
            my $name = $bit->[2]->{name};
            my $class = $bit->[2]->{class};
            my $id = $bit->[2]->{id};
            $current_text .= "<" . $bit->[1]
                           . ( $href  ? " href=\"$href\"" : "" )
                           . ( $name  ? " name=\"$name\"" : "" )
                           . ( $class ? " class=\"$class\"" : "" )
                           . ( $id    ? " id=\"$id\"" : "" )
                           . ">";
          } else {
            $current_text .= "<" . $bit->[1] . ">";
          }
        } elsif ( $bit->[0] eq "E" ) {
          $current_text .= "</" . $bit->[1] . ">";
        } elsif ( $bit->[0] eq "T" ) {
          $current_text .= $bit->[1];
        }
      }
      last;
    }
  }

  $current_text = encode_entities( $current_text );

  # put linebreaks back
  $current_text =~ s/&lt;br&gt;/\r\n/g;

  # Strip leading and trailing whitespace.
  $current_text =~ s/^\s+//;
  $current_text =~ s/\s+$//;

  my %tt_vars = (
                  base_url => $base_url,
                  cgi_url => $cgi_url,
                  textarea_name => $args{div_id},
                  current_text => $current_text,
                  page_to_edit => $args{page},
                  errmsg => $args{errmsg} || "",
                );
  print $q->header;
  $tt->process( "edit_static_page_form.tt", \%tt_vars ) || die $tt->error;
  exit 0;
}
