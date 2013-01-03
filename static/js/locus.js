function there_are_hard_parts() {
  return $('.hard').length > 0;
}

function initialize_hard_parts_display() {
  // Create and insert the image.
  $('<img class="folded_hard_part centered" src="/thegrandlocus_theme/static/images/penrose.png">').
	  clone().
	  insertBefore('.hard');
  // Register qTip event handler.
  $('.folded_hard_part').qtip(
    { id: 'penrose',
      prerender: true,
      content: 'Click to unfold technical part',
      position: {
        my: 'left center',
        at: 'right center'
      },
      show: {
        effect: function(offset) {$(this).show(100); }
      },
      hide: {
        event: 'click mouseleave'
      },
      style: {
        classes: 'ui-tooltip-bootstrap ui-tooltip-shadow'
      }
    }
  );
  // Register click event handler.
  $('.folded_hard_part').click(function() {
    $(this).next().fadeIn();
    $(this).hide();
  });
  // Hide the hard parts.
  $('.hard').hide();
  // Insert info at the top of the post.
  document.getElementById("hard_parts_info").innerHTML = 'This post contains <img src="/thegrandlocus_theme/static/images/penrose.png" height="16" width="16"> technical parts.';
}

function format_theme_style() {
  if (there_are_hard_parts()) {
    initialize_hard_parts_display();
  }

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

  // qTip event handler on RSS
  $('#rssicon').qtip(
    { id: 'rss', /* #ui-tooltip-rss */
      prerender: true,
      content: '... in a reader',
      position: {
        my: 'left center',
        at: 'right center'
      },
      style: {
        classes: 'ui-tooltip-bootstrap ui-tooltip-shadow'
      },
      show: {
        effect: function(offset) {$(this).show(100); }
      }
    }
  );
  $('#mailicon').qtip(
    { id: 'mail', /* #ui-tooltip-rss */
      prerender: true,
      content: '... by email',
      position: {
        my: 'left center',
        at: 'right center'
      },
      style: {
        classes: 'ui-tooltip-bootstrap ui-tooltip-shadow'
      },
      show: {
        effect: function(offset) {$(this).show(100); }
      }
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

