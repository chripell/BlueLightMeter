
"use strict";

var mockBLM = false;
var blmSynced = false;
var blmProfile = 'manual';
var blmMode = 0, blmIntTime = 0, blmHiGain = false, blmCH0 = 0, blmCH1 = 0, blmLux = 0, blmMaxLux = 0, blmMS = 0;

var profileMin = 100;
var profileMax = 5000;
var profileLast = 0;
var profileCur = 0;
var profileCh = false;
var profiles = {
    'all': [[false, 0], [false, 1], [true, 0], [false, 2], [true, 1], [true, 2]],
    'fast': [[false, 0], [true, 0], [true, 1], [true, 2]],
    'logain': [[false, 0], [false, 1], [false, 2], [true, 2]],
};

var msInterval = 402;

var calcMode = 'Av';
var flashMode = false;

var isoVals = ['100', '200', '400', '800', '1600', '3200', '6400'];
var tvVals = ['30', '15', '8', '4', '2', '1', '1/2', '1/4', '1/8', '1/15', '1/30', '1/60', '1/125', '1/250', '1/500', '1/1000', '1/2000', '1/4000', '1/8000'];
var avVals = ['1', '1.4', '2', '2.8', '4', '5.6', '8', '11', '16', '22', '32'];
var modeVals = ['13.7ms', '101ms', '402ms', 'Custom:'];
var buttonChanged = [];
var buttonVal = [];

var allLux = [];
var medLux = 0.0;
var maxLux = 0.0;
var medEV = 0.0;
var maxEV = 0.0;
var meanTimeMS = 3000.0;

function getID(t) {
    return t.replace('/', '_').replace('.', '_').replace(':', '_');
}

function addUL(ul, data, txt) {
    var items = [];
    $.each(data, function(i, item) {
	var id = getID(ul + item);
        items.push('<li><a href="#" id="' + id + '">' + item + '</a></li>');
    });
    $('#' + ul).append( items.join('') );
    $.each(data, function(i, item) {
	var id = getID(ul + item);
	$('#' + id).click(function(){
	    $('#' + txt).html(item + '<span class="caret"></span>');
	    buttonChanged[txt] = true;
	    buttonVal[txt] = item;
	});
    });
}

function updateControls() {
    $('#mode_button').html(modeVals[blmMode] + '<span class="caret"></span>');
    $('#higain_checkbox').prop('checked', blmHiGain);
    $('#cutom_time_ms').val(blmIntTime);
}

function calcMaxLux() {
    var now = Date.now();
    allLux.push([now, blmLux]);
    allLux = $.grep(allLux, function(x) {
	return x[0] >= (now - meanTimeMS);
    });
    medLux = 0.0;
    maxLux = 0.0;
    $.each(allLux, function(idx, x) {
	var v = x[1];
	if (v > maxLux) {
	    maxLux = v;
	}
	medLux += v;
    });
    medLux /= allLux.length;
}

function calcLux() {
    var d0 = blmCH0;
    var d1 = blmCH1;
    if (d0 == 0xffff || d1 == 0xffff) {
	return -1.0;
    }
    if (d0 == 0 || d1 == 0) {
        return 0.0;
    }
    var ratio = d1 / d0;
    d0 *= 402.0 / blmMS;
    d1 *= 402.0 / blmMS;
    if (!blmHiGain) {
        d0 *= 16.0;
        d1 *= 16.0;
    }
    if (ratio < 0.5) {
        return 0.0304 * d0 - 0.062 * d0 * Math.pow(ratio, 1.4);
    }
    if (ratio < 0.61) {
        return 0.0224 * d0 - 0.031 * d1;
    }
    if (ratio < 0.80) {
        return 0.0128 * d0 - 0.0153 * d1;
    }
    if (ratio < 1.30) {
        return 0.00146 * d0 - 0.00112 * d1;
    }
    return 0.0;
}

function makeFloat(v) {
    if (v.slice(0,2) == '1/')
	return 1.0 / parseFloat(v.slice(2));
    return parseFloat(v);
}

function findNear(val, l) {
    var min = 1e10;
    var ret = l[0];
    $.each(l, function(idx, i) {
        var diff = Math.abs(makeFloat(i) - val);
        if (diff < min) {
            ret = i;
            min = diff;
	}
    });
    return ret;
}

function calcExpo() {
    var ev;
    if (flashMode) {
	ev = maxEV;
    }
    else {
	ev = medEV;
    }
    if (calcMode == 'Av' || calcMode == 'Tv') {
	var deltaEV = Math.log2(parseInt(buttonVal['iso_button']) / 100.0);
	ev += deltaEV;
	var ev2 = Math.pow(2.0, ev);
	if (calcMode == 'Tv') {
	    var tv = Math.pow(parseFloat(buttonVal['Av_button']), 2.0) / ev2;
	    var tvn = findNear(tv, tvVals);
	    $('#result').html(tvn + ' s');
	}
	else {
	    var av = Math.sqrt(ev2 * makeFloat(buttonVal['Tv_button']))
	    var avn = findNear(av, avVals);
	    $('#result').html('f/' + avn);
	}
    }
    else {
	var evb = Math.log2(Math.pow(parseFloat(buttonVal['Av_button']), 2.0) /
			    makeFloat(buttonVal['Tv_button']));
	var isov = Math.pow(2.0, evb - ev);
	var isovn = findNear(isov, isoVals);
	$('#result').html(isovn + ' ISO');
    }
}

function sendConf(mode, higain, intTime) {
    switch(mode) {
    case 0:
	msInterval = 14;
	break;
    case 1:
	msInterval = 101;
	break;
    case 3:
	msInterval = 402;
	break;
    default:
	msInterval = intTime;
    }
    if (higain) {
	mode += 0x10;
    }
    var msb = Math.floor(intTime / 256);
    var lsb = intTime % 256;
    BLM.setParameters(mode.toString(16) + ' ' + lsb.toString(16) + ' ' + msb.toString(16));
}

function calcProfile() {
    if (blmProfile == 'manual') {
	if (buttonChanged['mode_button']) {
	    buttonChanged['mode_button'] = false;
	    var mode;
	    if (buttonVal['mode_button'] == '13.7ms') {
		mode = 0;
	    }
	    else if (buttonVal['mode_button'] == '101ms') {
		mode = 1;
	    }
	    else if (buttonVal['mode_button'] == '402ms') {
		mode = 2;
	    }
	    else {
		mode = 3;
	    }
	    sendConf(mode, $('#higain_checkbox').is(":checked"), $('#cutom_time_ms').val());
	}
    }
    else {
	var profile = profiles[blmProfile];
	var now = (new Date).getTime();
	while (profileCur >= profile.length) {
	    profileCur--;
	}
	if (now > profileLast + 1000) {
	    profileLast = now;
	    if ((blmCH0 < profileMin || blmCH1 < profileMin) && profileCur < (profile.length - 1)) {
		profileCur++;
		profileCh = true;
	    }
	    if ((blmCH0 > profileMax || blmCH1 > profileMax) && profileCur > 0) {
		profileCur--;
		profileCh = true;
	    }
	}
	if (profileCh) {
	    profileCh = false;
	    sendConf(profile[profileCur][1], profile[profileCur][0], $('#cutom_time_ms').val());
	}
	updateControls();
    }
}

function readLux() {
    if (mockBLM) {
	blmCH0 = 11;
	blmCH1 = 12;
        blmMode = 2;
        blmHiGain = false;
        blmIntTime = 666;
	blmMS = 13.7;
	blmLux = 500.0;
	blmMaxLux = 0.0;
	blmSynced = true;
    }
    else {
	var rs = BLM.getData();
	var r = rs.split(' ');
	if (r[0] == 'initializing:') {
	    $('#blm_status').html('Status: initializing(' + BLM.getStatus() + ').');
	}
	else if (r[0] == 'nolux:') {
	    $('#blm_status').html('Status: ERROR(' + BLM.getStatus() + ').');
	} 
	else if (r[0] == 'status:' || r[0] == 'nodata:') {
	    $('#blm_status').html('Status: ' + BLM.getStatus() + '.');
	} 
	else if (r[0] == 'lux:') {
	    $('#blm_status').html('Status: no BLM, using internal light meter(' +
				  BLM.getStatus() + ').');
	    blmLux = parseFloat(r[1]);
	} 
	else if (r[0] == 'blm:') {
	    if (r.length > 7) {
		var raw = $.map(r.slice(1), function(x) {
		    return parseInt(x, 16);
		});
		blmCH0 = raw[2] + raw[3] * 256;
		blmCH1 = raw[4] + raw[5] * 256;
		blmMode = raw[6] & 0x3;
		blmHiGain = (raw[6] & 0x10) > 0;
		blmIntTime = raw[7] + raw[8] * 256;
		if (blmMode == 0) {
		    blmMS = 13.7;
		}
		else if (blmMode == 1) {
		    blmMS = 101.0;
		}
		else if (blmMode == 2) {
		    blmMS = 402.0;
		}
		else {
		    blmMS = blmIntTime;
		}
		blmLux = calcLux();
		if (!blmSynced) {
		    blmSynced = true;
		    updateControls();
		}
	    }
	}
	else {
	    var m = 'Status: INTERNAL ERROR, unexpected read: ' + r +'(status: ' +
		BLM.getStatus() + ').';
	    console.log(m);
	    $('#blm_status').html(m);
	}
    }
    calcMaxLux();
    $('#cur_lux').text('Lux: ' + medLux.toFixed(2));
    $('#max_lux').text('MaxLux: ' + maxLux.toFixed(2));
    if (medLux > 0.0) {
	medEV = Math.log2(medLux / 2.5);
	$('#cur_ev').text('EV: ' + medEV.toFixed(1));
    }
    else {
	$('#cur_ev').text('EV: N/A');
    }
    if (maxLux > 0.0) {
	maxEV = Math.log2(maxLux / 2.5);
	$('#max_ev').text('MaxEV: ' + maxEV.toFixed(1));
    }
    else {
	$('#max_ev').text('MaxEV: N/A');
    }
    calcExpo();
    if (blmSynced) {
	calcProfile();
	var lux = 0.0;
	if (!mockBLM) {
	    lux = BLM.getLux();
	}
	$('#blm_status').html('Debug: ch:' + blmCH0 + ',' + blmCH1 + ' par:' + blmMode +
			      ',' + blmHiGain + ',' + blmIntTime + ' lux:' + lux);
    }
    setTimeout(readLux, msInterval);
}

$(document).ready(function() {
    console.log( 'BLM JS ready!' );
    addUL('iso_list', isoVals, 'iso_button');
    buttonVal['iso_button'] = '100';
    addUL('av_list', avVals, 'Av_button');
    buttonVal['Av_button'] = '1';
    addUL('tv_list', tvVals, 'Tv_button');
    buttonVal['Tv_button'] = '1';
    addUL('mode_list', modeVals, 'mode_button');
    $('#Av_div').addClass('hidden');
    $('#calc_Av').click(function(){
	calcMode = 'Av';
	$('#Av_div').addClass('hidden');
	$('#Tv_div').removeClass('hidden');
	$('#iso_div').removeClass('hidden');
    });
    $('#calc_Tv').click(function(){
	calcMode = 'Tv';
	$('#Av_div').removeClass('hidden');
	$('#Tv_div').addClass('hidden');
	$('#iso_div').removeClass('hidden');
    });
    $('#calc_ISO').click(function(){
	calcMode = 'ISO';
	$('#Av_div').removeClass('hidden');
	$('#Tv_div').removeClass('hidden');
	$('#iso_div').addClass('hidden');
    });
    $('#mode_flash').click(function(){
	flashMode = true;
    });
    $('#mode_noflash').click(function(){
	flashMode = false;
    });
    $('#mode_noflash').click(function(){
	flashMode = false;
    });
    $('#profile_manual').click(function(){
	blmProfile = 'manual';
	profileCh = true;
    });
    $('#profile_all').click(function(){
	blmProfile = 'all';
	profileCh = true;
    });
    $('#profile_fast').click(function(){
	blmProfile = 'fast';
	profileCh = true;
    });
    $('#profile_logain').click(function(){
	blmProfile = 'logain';
	profileCh = true;
    });
    $('#cutom_time_ms').change(function(){
	buttonChanged['mode_button'] = true;
    });
    $('#higain_checkbox').change(function(){
	buttonChanged['mode_button'] = true;
    });
    setTimeout(readLux, msInterval);
});
