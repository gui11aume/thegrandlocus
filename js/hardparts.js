function reformat() {
  prettyPrint();
  if (there_are_hard_parts()) {
    initialize_hard_parts_display();
  }
  else {
    $('#hard_parts_info').replaceWith('<br/>');
  }
}

function there_are_hard_parts() {
  return $('.hard').length > 0;
}

function initialize_hard_parts_display() {
  // Create and insert the image.
  $('<img class="folded_hard_part centered" src="/img/moebius.png">').
	  clone().
	  insertBefore('.hard');
  // Register click event handler.
  $('.folded_hard_part').click(function() {
    $(this).hide();
    $(this).next().show(300);
  });
  // Register hover event handler (hand cursor when hovering).
  // Hide the hard parts.
  $('.hard').hide();
}
