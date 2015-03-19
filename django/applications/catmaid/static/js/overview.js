/**
 * Overview navigator widget
 */
function Overview( stack )
{
	/**
	 * get the view object
	 */
	this.getView = function()
	{
		return view;
	};
	
	var onmousedown =
	{
		jump : function( e )
		{
			var m = CATMAID.ui.getMouse( e, self.getView() );
			if ( m )
			{
				//statusBar.replaceLast( m.offsetX + ", " + m.offsetY );
				stack.moveToPixel( stack.z, Math.round( m.offsetY / scale ), Math.round( m.offsetX / scale ), stack.s );
			}
			return false;
		},
		drag : function( e )
		{
			CATMAID.ui.registerEvent( "onmousemove", onmousemove );
			CATMAID.ui.registerEvent( "onmouseup", onmouseup );
			CATMAID.ui.catchEvents( "move" );
			CATMAID.ui.onmousedown( e );
		
			CATMAID.ui.catchFocus();
		
			return false;
		}
	};
	
	var onmousemove = function( e )
	{
		stack.moveToPixel( stack.z,
                           stack.y + CATMAID.ui.diffY / scale,
                           stack.x + CATMAID.ui.diffX / scale,
                           stack.s );
		return false;
	};
	
	var onmouseup = function( e )
	{
		CATMAID.ui.releaseEvents();
		CATMAID.ui.removeEvent( "onmousemove", onmousemove );
		CATMAID.ui.removeEvent( "onmouseup", onmouseup );
		return false;
	};	
	
	this.redraw = function()
	{
		var $view = $( view );
		// If it is minimized, don't redraw. Avoids fetching and decoding an extra jpeg
		if ( $view.hasClass( 'smallMapView_hidden' ) ) return;

		if ( typeof scale === "undefined" )
		{
			var scaleY = parseInt( $view.css( 'max-height' ) ) / maxY;
			var scaleX = parseInt( $view.css( 'max-width' ) ) / maxX;
			scale = Math.min( scaleX, scaleY );
		}

		var height = scale / stack.scale * stack.viewHeight;
		var width = scale / stack.scale * stack.viewWidth;
		rect.style.height = Math.floor( height ) + "px";
		rect.style.width = Math.floor( width ) + "px";
		rect.style.top = Math.floor( scale * stack.y - height / 2 ) + "px";
		rect.style.left = Math.floor( scale * stack.x - width / 2 ) + "px";
		
		for ( var layer in layers )
			layers[ layer ].redraw();
		
		return;
	};
	
	/**
	 * Add a layer.  Layers are associated by a unique key.
	 * If a layer with the passed key exists, then this layer will be replaced.
	 * 
	 * @param key
	 * @param layer
	 */
	this.addLayer = function( key, layer )
	{
		if ( layers[ key ] )
			layers[ key ].unregister();
		layers[ key ] = layer;
		return;
	};
	
	/**
	 * Remove a layer specified by its key.  If no layer with this key exists,
	 * then nothing will happen.  The layer is returned;
	 * 
	 */
	this.removeLayer = function( key )
	{
		var layer = layers[ key ];
		if ( typeof layer != "undefined" && layer )
		{
			layer.unregister();
			delete layers[ key ];
			return layer;
		}
		else
			return null;
	};
	
	var self = this;
	
	var layers = {};
	
	// initialize
	var maxX = stack.dimension.x - 1;
	var maxY = stack.dimension.y - 1;
	var scale;

	var view = document.createElement( "div" );
	view.className = "smallMapView";
	view.onmousedown = onmousedown.jump;

	var rect = document.createElement( "div" );
	rect.className = "smallMapRect";
	rect.onmousedown = onmousedown.drag;
	view.appendChild( rect );

    var hide = function() {
        toggle.title = "show overview";
        view.className = "smallMapView_hidden";
    };

    var show = function() {
        toggle.title = "hide overview";
        view.className = "smallMapView";
        self.redraw();
    };
	
	var toggle = document.createElement( "div" );
	toggle.className = "smallMapToggle";
	toggle.title = "hide general view";
	toggle.onmousedown = function( e )
	{
		if ( typeof event != "undefined" && event )
			event.cancelBubble = true;
		if ( e && e.stopPropagation )
			e.stopPropagation();

		if ( view.className == "smallMapView_hidden" )
		{
            show();
		}
		else
		{
            hide();
		}
		return false;
	};
	
	view.appendChild( toggle );

    // hide small maps by default
    hide();
}

