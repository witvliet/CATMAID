/**
 * imageCache.js - image caching framework.
 * Zoltan Hawryluk - http://www.useragentman.com/
 * MIT License.
 *
 * Modified: Stephan Gerhard, November 2013
 */

var imageCache = new function () {
	var me = this;
		
	me.push = function (src, loadEvent) {
		var item = new Image();
		if (loadEvent) {
			item.onload = loadEvent;
			item.onerror = function(e) {
				console.log('error loading', src);
			};
		}
		item.src =  src;
	}
	me.pushArray = function (array, imageLoadEvent, imagesLoadEvent) {
		var numLoaded = 0;
		var arrayLength = array.length;
		for (var i=0; i<arrayLength; i++) {
			me.push(array[i], function (e) {
				if (imageLoadEvent) {
					setTimeout(function () {
						imageLoadEvent(e);
					}, 10)
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
