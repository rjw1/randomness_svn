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
use PubSite;
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
if ( $page eq "updates" ) {
  print $q->redirect( $base_url . "admin/upload-updates-info.cgi" );
  exit 0;
}
if ( $page ne "front" && $page ne "notes" ) {
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

  my $current_text = PubSite->extract_html( file   => $args{page_file},
                                            div_id => $args{div_id} );
  if ( !$current_text ) {
    $args{errmsg} .= " Couldn't extract $args{div_id} from $args{page_file}.";
  }

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
