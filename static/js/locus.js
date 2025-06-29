function there_are_hard_parts() {
  return $('.hard').length > 0;
}

function format_exercises() {
  // Add link to show ansers.
  $('<a href="javascript:;" class="show_answer">Show answers</a>').insertBefore('.answer');
  // Register click event handler.
  $('.show_answer').click(function() {
    $(this).next().show();
    $(this).hide();
  });
  // Hide answers.
  $('.answer').hide();
}

function initialize_hard_parts_display() {
  // Create and insert the image.
  $('<img class="folded_hard_part centered" src="/static/images/penrose.png">').
	  clone().
	  insertBefore('.hard');
  // Register click event handler.
  $('.folded_hard_part').click(function() {
    $(this).next().fadeIn();
    $(this).hide();
  });
  // Hide the hard parts.
  $('.hard').hide();
}

function format_theme_style() {

  // Initial format of hard parts.
  if (there_are_hard_parts()) {
    initialize_hard_parts_display();
  }

  format_exercises();

  // White dots on the right navigation panel.
  // Get the section we're in. Append a white dot next to the link.
  var section = $('#section').attr("title");
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

  // Table hover highlight.
  $("tr._highlight").hover(
      function() { $(this).addClass("highlight"); },
      function() { $(this).removeClass("highlight"); }
  );

}
