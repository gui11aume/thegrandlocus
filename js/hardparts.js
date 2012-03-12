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
  $('<img class="folded_hard_part centered" src="/img/moebius.png">').clone().insertBefore('.hard');
  $('.folded_hard_part').click(function() {
    $(this).hide();
    $(this).next().show(300);
  });
  $('.hard').hide();
}
