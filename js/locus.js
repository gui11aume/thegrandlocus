function reformat() {
  $('pre').addClass('prettyprint');
  prettyPrint();
  if (there_are_hard_parts()) {
    initialize_hard_parts_display();
  }
  else {
    $('#hard_parts_info').replaceWith('<br/>');
  }
  white_dots();
}

function there_are_hard_parts() {
  return $('.hard').length > 0;
}

function initialize_hard_parts_display() {
  // Create and insert the image.
  $('<img class="folded_hard_part centered" src="/img/moebius.png">').
	  clone().
	  insertBefore('.hard');
  // Register qTip event handler.
  $('.folded_hard_part').qtip(
    { content: 'Click to unfold technical part.' }
  );
  // Register click event handler.
  $('.folded_hard_part').click(function() {
    $(this).hide();
    $(this).next().show(300);
  });
  // Hide the hard parts.
  $('.hard').hide();
}

function white_dots() {
  // Get the section we're in. Append a white dot next to the link.
  var section = $('#section').text();
  $(section).addClass('whitedot');
  $(section).prepend($('<span>• </span>'));
  $(section).append($('<span> •</span>'));
  // Register hover event handler (white dots next to links).
  $('.navigation_link:not(.whitedot)').hover(
    function() {
      $(this).prepend($('<span class="hover_white_dot">• </span>'));
      $(this).append($('<span class="hover_white_dot"> •</span>'));
    },
    function() {
      $(this).find(".hover_white_dot").remove();
    }
  );
}

function print_mail(text) {
  at = '@';
  me = 'guillaume';
  mydomain = 'thegrandlocus.com';
  document.write(
    '<a href="mailto:' + me + at + mydomain + '">' + text + '</a>'
  );
}
