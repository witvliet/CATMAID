/**
 * imageCache.js - image caching framework.
 * Zoltan Hawryluk - http://www.useragentman.com/
 * MIT License.
 *
 * Modified: Stephan Gerhard, November 2013
 */

var imageCache = new function () {
	var me = this;
	     
    var cache = {};

	me.push = function (src, loadEvent) {
		var item = new Image();
		if (cache[src] && loadEvent) {
			console.log('already in cache only execute loadevent');
        	loadEvent(src);
        } else {
			if (loadEvent) {
				item.onload = loadEvent;
				/*item.onerror = function(e) {
					console.log('error loading', src);
				};*/
			}
			cache[src]=item;
        }
		item.src =  src;
	}
	me.pushArray = function (array, imageLoadEvent, imagesLoadEvent) {
		var numLoaded = 0;
		var arrayLength = array.length;
		for (var i=0; i<arrayLength; i++) {
			me.push(array[i], function (e) {
				console.log('numloaded', numLoaded, 'with src', e);
				if (imageLoadEvent) {
					imageLoadEvent(e);
				}
				numLoaded++;
				if (numLoaded == arrayLength) {
					setTimeout(function () {
						imagesLoadEvent(e);
					}, 1)
				}
			})
		}
	}
	
}
