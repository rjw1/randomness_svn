package Wiki::Toolkit::Search::Plucene;

use strict;
use Carp "croak";
use File::Spec::Functions qw(catfile);
use Plucene::Document;
use Plucene::Document::Field;
use Plucene::Index::Writer;
use Plucene::Analysis::SimpleAnalyzer;
use Plucene::QueryParser;
use Plucene::Search::IndexSearcher;
use Plucene::Search::HitCollector;

use vars qw( @ISA $VERSION );

$VERSION = '0.02';
use base 'Wiki::Toolkit::Search::Base';

=head1 NAME

Wiki::Toolkit::Search::Plucene - Use Plucene to search your Wiki::Toolkit wiki.

=head1 SYNOPSIS

  my $search = Wiki::Toolkit::Search::Plucene->new( path => "/var/plucene/wiki" );
  my %wombat_nodes = $search->search_nodes("wombat");

Provides search-related methods for L<Wiki::Toolkit>.

This is a modified version of the CPAN module.  It ignores text inside the
"neighbours" div.

=cut

=head1 METHODS

=over 4

=item B<new>

  my $search = Wiki::Toolkit::Search::Plucene->new( path => "/var/plucene/wiki" );

Takes only one parameter, which is mandatory. C<path> must be a directory
for storing the indexed data.  It should exist and be writeable.

=cut

sub _init {
    my ($self, %args) = @_;
    $self->{_dir} = $args{path};
    return $self;
}

sub _dir { shift->{_dir} }

sub _parsed_query {
        my ($self, $query, $default) = @_;
        my $parser = Plucene::QueryParser->new({
                        analyzer => Plucene::Analysis::SimpleAnalyzer->new(),
                        default  => $default
                });
        $parser->parse($query);
}

# Make new searchers, readers and writers each time we're asked for
# one - if we made them in _init then they would always think the index
# has the same stuff in as it had when they were made.

sub _searcher {
    my $self = shift;
    return Plucene::Search::IndexSearcher->new( $self->_dir );
}
sub _reader {
    my $self = shift;
    return Plucene::Index::Reader->open( $self->_dir );
}

sub _writer {
        my $self = shift;
        return Plucene::Index::Writer->new(
                $self->_dir,
                Plucene::Analysis::SimpleAnalyzer->new,
                -e catfile($self->_dir, "segments") ? 0 : 1
        );
}

sub _search_nodes {
    my ($self, $query, $and_or) = @_;
    # Bail and return empty list if nothing stored in directory.
    if ( ! -e catfile($self->_dir, "segments") ) {
        return ();
    }
    local $Plucene::QueryParser::DefaultOperator = "AND"
        unless ( $and_or and lc($and_or) eq "or" );
    my @docs;
    my $searcher = $self->_searcher;
    my $hc       = Plucene::Search::HitCollector->new(
                collect => sub {
                        my ($self, $doc, $score) = @_;
                        my $res = eval { $searcher->doc($doc) };
                        push @docs, [ $res, $score ] if $res;
                });
    my $parsed_query = $self->_parsed_query( $query, 'text' );
    $searcher->search_hc($parsed_query, $hc);
    @docs = map $_->[0]->get("id")->string, sort { $b->[1] <=> $a->[1] } @docs;
    return @docs;
}

sub search_nodes {
    my ($self, @args) = @_;
    my @docs = $self->_search_nodes( @args );
    my $i = 1;
    return map { $_ => $i++ } @docs;
}

sub _fuzzy_match {
    my ($self, $string, $canonical) = @_;
    return map { $_ => ($_ eq $string ? 2 : 1) } 
           $self->_search_nodes("fuzzy:$canonical");
}

sub index_node {
    my ($self, $node, $content) = @_;
    my $writer = $self->_writer;
    my $doc    = Plucene::Document->new;
    my $fuzzy = $self->canonicalise_title( $node );

    # Ignore stuff inside div.neighbours.
    $content =~ s|<div class="neighbours">.*?</div>||gs;

    $doc->add( Plucene::Document::Field->Text( "content", join( " ", $node, $content ) ) );
    $doc->add( Plucene::Document::Field->Text( "fuzzy", $fuzzy ) );
    $doc->add( Plucene::Document::Field->Text( "title", $node ) );
    $doc->add(Plucene::Document::Field->Keyword(id => $node));
    $doc->add(Plucene::Document::Field->UnStored('text' => join( " ", $node, $content )));
    $writer->add_document($doc);
}

sub optimize { shift->_writer->optimize() }

sub indexed {
    my ($self, $id) = @_;
    my $term = Plucene::Index::Term->new({ field => 'id', text => $id });
    return $self->_reader->doc_freq($term);
}

sub delete_node {
    my ($self, $id) = @_;
    my $reader = $self->_reader;
    $reader->delete_term(
                 Plucene::Index::Term->new({ field => "id", text => $id }));
    $reader->close;
}

sub supports_phrase_searches { return 1; }
sub supports_fuzzy_searches  { return 1; }

=back

=head1 SEE ALSO

L<Wiki::Toolkit>, L<Wiki::Toolkit::Search::Base>.

=cut

1;
