
$(document).ready(function() {
    console.log( 'BLM JS ready!' );
    var intervalID = setInterval(function(){
	$('#status-bar').text(BLM.getStatus());
	$('#mode-bar').text(BLM.getMode());
	$('#data-bar').text(BLM.getData());
	$('#lux-bar').text(BLM.getLux());
    }, 1000);
});
