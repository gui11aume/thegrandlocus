$(document).ready(add_bubbles);

function add_bubbles() {
   $('.prep').map(function() {
      if ($(this).attr('data-comments')) {
         $(this).qtip({
            content: {
               text: function(api) { return $(this).attr('data-comments'); }
            },
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
         });
      }
   });
}

function draw_plasmid() {
// Canvas is 320x320.
  var graph = document.getElementById("graph");
  var g = graph.getContext("2d");
  // Use method 'arc' with an angle of 2 x pi.
  g.arc(160, 160, 150, 0, Math.PI*2, true);
  g.lineWidth = 3;
  g.stroke();
}

function write_plasmid_info() {
  var graph = document.getElementById("graph");
  var g = graph.getContext("2d");
  var plasmid_id = $('#plasmid_id').attr('data-name');
  var size = "(" + $('#full_sequence').text().length +" bp)";
  g.fillStyle = "black";
  g.textAlign = "center";
  g.font = "18px serif";
  g.textBaseline = "bottom";
  g.fillText(plasmid_id, 160, 155);
  g.font = "14px serif";
  g.textBaseline = "top";
  g.fillText(size, 160, 160);
}

function draw_feature(start, end, ftype) {
// start is a number from 0 to 1.
// length is a number from 0 to 1.
// canvas is 400x250.

var ftype_colors = {
   gene: "royalblue",
   promoter: "brown",
   origin: "darkseagreen",
   other: "indigo",
};

var color = ftype_colors[ftype];

start_angle = start*2*Math.PI;
  end_angle = end*2*Math.PI;
  x_start = 160 + 155*Math.cos(-start_angle);
  y_start = 160 + 155*Math.sin(start_angle);
  x_end = 160 + 155*Math.cos(-end_angle);
  y_end = 160 + 155*Math.sin(end_angle);

var graph = document.getElementById("graph");
  var g = graph.getContext("2d");
  g.beginPath();
  g.moveTo(x_start, y_start);
  g.lineTo(150, 160);
  g.lineTo(x_end, y_end);
  g.strokeStyle = color;
  g.fill();
  g.arc(160, 160, 155, start_angle, end_angle, false);
  g.fillStyle = color;
  g.lineWidth = 0;
  g.fill();

g.beginPath();
  g.arc(160, 160, 145, 0, Math.PI*2, false);
  //Draw a small white circle inside the plasmid.
  g.fillStyle = "#FFFFFF";
  g.fill();
}

function select_sequence(start, end) {
  // Side effect function to set sequence selection to 'start', 'end'.
  var range = document.createRange();
  range.setStart(
        document.getElementById('full_sequence').firstChild, start);
  range.setEnd(
        document.getElementById('full_sequence').firstChild, end);
  var sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);
}
