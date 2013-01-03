function replace_title() {
   var init_pos = $('#post_title').offset();
   var h1_width = $('#post_title').width();
   var title = $('#post_title').text();
   for (i = 0 ; i < title.length ; i++) {
     letter = /\s/.test(title[i]) ? '&nbsp;' : title[i];
     $('body').append('<div class="moving_letter">' + letter + '</div>');
   }
   $('.moving_letter').css({
     'position': 'absolute',
     'font-family': $('#post_title').css('font-family'),
     'font-size': $('#post_title').css('font-size'),
     'font-weight': $('#post_title').css('font-weight'),
     'color': $('#post_title').css('color')
   });
   _width = $('.moving_letter').map(function() {
     return $(this).width();
   });
   title_length = 0;
   for (i = 0 ; i < _width.length ; i++) {
     title_length += _width[i];
   }
   cum_width = [init_pos.left + (h1_width - title_length)/2];
   for (i = 0 ; i < _width.length ; i++) {
     cum_width.push(cum_width[i] + _width[i]);
   }
   $('.moving_letter').offset(function(index, coords) {
     return { 'top': init_pos.top, 'left': cum_width[index] };
   });
   $('#post_title').css('visibility', 'hidden');
}

function changePosition() {
   $('.moving_letter').css({
     'top': function(index, value) {
       return parseInt(value) + 2*(Math.random()-.25);
     },
     'left': function(index, value) {
       return parseInt(value) + 2*(Math.random()-.25);
     }
   });
}

$(window).load(function() {
   setTimeout("replace_title()", 5000);
   window.setInterval("changePosition()", 20);
});
