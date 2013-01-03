window.onload = start_showdown;

var converter;
var preview_timer;
var lastText,lastOutput;
var input,preview;


function start_showdown() {

   input = document.getElementById("message");
   input_title = document.getElementById("name");
   preview = document.getElementById("preview");
   preview_title = document.getElementById("preview_title");
   converter = new Showdown.converter();

   window.onkeyup = input.onkeyup = onInput;

   if (input.addEventListener) {
      input.addEventListener("input", onInput, false);
   }

   update_preview();

}


function update_preview() {

   var text = input.value;
   text = converter.makeHtml(text);
   preview.innerHTML = text;
   preview_title.innerHTML = input_title.value;
   lastOutput = text;

   MathJax.Hub.Queue(["Typeset", MathJax.Hub]);

}


function onInput() {
   
   if (preview_timer) {
      window.clearTimeout(preview_timer);
      preview_timer = undefined;
   }
   preview_timer = window.setTimeout(update_preview, 1000);
}

