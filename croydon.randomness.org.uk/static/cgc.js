var history_text;

$(
  function() {
    // Hide the historical info by default.
    history_text = $( 'div.history' ).html();
    hide_history();
  }
);

var show_button = '<p>(<a href="#" class="show_history">show historical info</a>)</p>';
var hide_button = '<p>(<a href="#" class="hide_history">hide historical info</a>)</p>';

function hide_history() {
  $( 'div.history' ).html( show_button );
  $( 'a.show_history' ).click(
    function() {
      show_history();
      return false;
    }
  );
}

function show_history() {
  $( 'div.history' ).html( hide_button + history_text + hide_button );
  $( 'a.hide_history' ).click(
    function() {
      hide_history();
      return false;
    }
  );
}