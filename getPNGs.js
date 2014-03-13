var args = require('system').args;
var port = args[1];
console.log("running on port:: "  + port);
var server = require('webserver').create();
var root = "/home/bhoomit/data/";
var service = server.listen(port, function(request, response) {
    var page = require('webpage').create();
	var page2 = require('webpage').create();

	var fs = require("fs");
	page.clipRect = { top: 0, left: 0, width: 1920, height: 1080};
	page.viewportSize = { width: 1920, height: 1080};

	var url = 'http://code-school-41741.apne1.actionbox.io:8000/html/simple.html?latlng1=' + request.post.latlng1 + '&latlng2=' + request.post.latlng2 + '&title=' + request.post.title;
	console.log(url);
	page.open(url, function(status) {console.log('Status: ' + status);});
	var interval = null
	var ts = new Date().getTime().toString();
	var exitCount = 0;
	page.onCallback = function(data) {
	    console.log('PC :: ' + data.ev);
	    if(data.ev == 'render'){
			var file_name = ('00'+data.position).slice(-3) +'.png'
	    		page.render( root + 'temp/' + ts + '/' + ts + '_' + file_name);
	    }else if(data.ev == 'error'){
	    	var errorPage = require('webpage').create();
	    	errorPage.open("http://localhost:8089/phantomError?message=" + data.message + '&latlng1=' + request.post.latlng1 + '&latlng2=' + request.post.latlng2 + '&title=' + request.post.title, function(status) {errorPage.release();});
	    }else if(data.ev == 'errorExit'){
	    	var errorPage = require('webpage').create();
	    	errorPage.open("http://localhost:8089/phantomError?message=" + data.message + '&latlng1=' + request.post.latlng1 + '&latlng2=' + request.post.latlng2 + '&title=' + request.post.title, function(status) {errorPage.release();});
	    	page.release();
	    	page2.release();
		    console.log('exit:: ' + ts);
		    response.statusCode = 200;
		    response.write(ts);
		    response.close();
	    }else if(data.ev == 'exit'){
	    	page.release();
		    console.log('exit:: ' + ts);
		    response.statusCode = 200;
		    response.write(ts);
		    response.close();
		    console.log(request.post.callback + ts + '/' + request.post.latlng1 + "::" + request.post.latlng2);
		    setTimeout(function(){
		    	page2.open(request.post.callback + ts + '/' + request.post.latlng1 + "::" + request.post.latlng2,function(status){
		    		console.log("callback status::" + status);
		    		page2.release();
		    	});	
		    },1000);
		    
	    }
	};
	
});
