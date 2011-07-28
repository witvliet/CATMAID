/**
 * stack.js
 *
 * requirements:
 *	 tools.js
 *	 ui.js
 *	 slider.js
 */

/**
 */

/**
 * Stack is the core data viewer and interaction element.  It displays a list
 * of layers of an x,y-plane in an n-dimensional data set, tracks the
 * navigation/edit mode and organizes access to user interface elements such
 * as navigation sliders and buttons.  x, y dimensions are shown in the plane,
 * for all other dimensions, a slider is used.
 * 
 * Layers can be images, text, SVG or arbitrary other overlays.
 * 
 * A Stack is created with a given pixel resolution, pixel dimension, a
 * translation relative to the project and lists of planes to be excluded
 * (e.g. missing sections in serial section microscopy and missing frames in a
 * time series).  These properties limit the field of view and the slider
 * ranges.  
 */
function Stack(
		project,					//!< {Project} reference to the parent project
		id,							//!< {Integer} the stack's id
		title,						//!< {String} the stack's title
		dimension,					//!< {Array} pixel dimensions [x, y, z, ...]
		resolution,					//!< {Array} physical resolution in units/pixel [x, y, z, ...]
		translation,				//!< @todo replace by an affine transform
		skip_planes,				//!< {Array} planes to be excluded from the stack's view [[z,t,...], [z,t,...], ...]
		trakem2_project				//!< {boolean} that states if a TrakEM2 project is available for this stack
)
{
	var n = dimension.length;
	
	/**
	 * update the scale bar (x-resolution) to a proper size
	 */
	var updateScaleBar = function()
	{
		var meter = self.scale / resolution[ 0 ];
		var width = 0;
		var text = "";
		for ( var i = 0; i < Stack.SCALE_BAR_SIZES.length; ++i )
		{
			text = Stack.SCALE_BAR_SIZES[ i ];
			width = Stack.SCALE_BAR_SIZES[ i ] * meter;
			if ( width > Math.min( 192, self.viewWidth / 5 ) )
				break;
		}
		var ui = 0;
		while ( text >= 1000 && ui < Stack.SCALE_BAR_UNITS.length - 1 )
		{
			text /= 1000;
			++ui;
		}
		scaleBar.style.width = width + "px";
		scaleBar.firstChild.firstChild.replaceChild(
			document.createTextNode( text + " " + Stack.SCALE_BAR_UNITS[ ui ] ),
			scaleBar.firstChild.firstChild.firstChild );
		return;
	}
	
	/**
	 * update all state informations and the screen content
	 */
	var update = function( now )
	{
		self.overview.redraw();
		updateScaleBar();
		
		//statusBar.replaceLast( "[" + ( Math.round( x * 10000 * resolution[0] ) / 10000 ) + ", " + ( Math.round( y * 10000 * resolution[1] ) / 10000 ) + "]" );
		
		if ( !transition.queued( redraw ) )
		{
			if ( now )
				transition.register( redraw );
			else
				redraw();
		}
		
		return
	}
	
	/**
	 * Get stack coordinates of the current view's top left corner.
	 * These values might be used as an offset to get the stack coordinates of a
	 * mouse event handled by the stack.
	 */
	this.screenPosition = function()
	{
		var width = self.viewWidth / self.scale;
		var height = self.viewHeight / self.scale;
		var l =
		{
			top : Math.floor( self.pos[1] - height / 2 ),
			left : Math.floor( self.pos[0] - width / 2 )
		};
		return l;
	}
	
	/**
	 * Get the project coordinates of the current view.
	 */
	this.projectCoordinates = function()
	{
		var l = new Array();
		for ( var i = 0; i < n; ++i )
		{
			l[i] = self.pos[i] * resolution[i] + translation[i];
		}
		return l;
	}

  /*
   * Get the top and left coordinates in physical project coordinates of
   * stack's window
   */
  this.getWorldTopLeft = function()
  {
    return {
      worldTop : ( ( self.pos[0] - self.viewHeight / self.scale / 2 ) ) * self.resolution[1] + self.translation[1],
      worldLeft : ( ( self.pos[0] - self.viewWidth / self.scale / 2 ) ) * self.resolution[0] + self.translation[0],
      scale : self.scale
    }
  }
  
	/**
	 * align and update the tiles to be ( x, y ) in the image center
	 */
	var redraw = function()
	{
		self.yc = Math.floor( self.pos[1] * self.scale - ( self.viewHeight / 2 ) );
		self.xc = Math.floor( self.pos[0] * self.scale - ( self.viewWidth / 2 ) );

		for ( var key in layers )
			layers[ key ].redraw();
			
		//----------------------------------------------------------------------
		/**
		 * This question is completely useless but without asking it, Firefox on
		 * Linux systems will not redraw the screen properly.  Took me ... to
		 * find this out.
		 */
		var a = view.offsetWidth;
		//----------------------------------------------------------------------
		
		for ( var i = 0; i < n; ++i )
		{
			self.old_pos[i] = self.pos[i];
		}
		self.old_s = self.s;
		self.old_scale = self.scale;
		self.old_yc = self.yc;
		self.old_xc = self.xc
		
		return 2;
	}
	
	/**
	 * get the view element
	 */
	this.getView = function()
	{
		return view;
	}
	
	/**
	 * move to project-coordinates
	 */
	this.moveTo = function( posp, sp )
	{
		if ( typeof sp == "number" )
		{
			self.s = Math.max( 0, Math.min( self.MAX_S, Math.round( sp ) ) );
			self.scale = 1 / Math.pow( 2, self.s );
		}
		
		for ( var i = 0; i < n; ++i ) {
			self.pos[i] = Math.max( 0, Math.min( max[i], Math.round( ( posp[i] - translation[i] ) / resolution[i] ) ) );
			// TODO: handle broken slices for n dimensions
			if ( i == 2 ) {
				var z1;
				var z2;
				z1 = z2 = Math.round( ( posp[2] - translation[2] ) / resolution[2] );
				while ( skip_planes[ z1 ] && skip_planes[ z2 ] )
				{
					z1 = Math.max( 0, z1 - 1 );
					z2 = Math.min( max[2], z2 + 1 );
				}
				if ( !skip_planes[ z1 ] ) self.pos[2] = z1;
				else self.pos[2] = z2;
				self.pos[2] = Math.max( 0, Math.min( max[2], self.pos[2] ) );
			}
		}
		
		update();
		
		return;
	}
	
	/**
	 * move to pixel coordinates
	 */
	this.moveToPixel = function( posp, sp )
	{
		self.s = Math.max( 0, Math.min( self.MAX_S, sp ) );
		self.scale = 1 / Math.pow( 2, self.s );
		
		var p = new Array();
		for ( var i = 0; i < n; ++i )
		{
			p[i] = posp[i] * resolution[i] + translation[i];
		}
		project.moveTo( p );
		
		return true;
	}
	
	var resize = function()
	{
		self.viewWidth = stackWindow.getFrame().offsetWidth;
		self.viewHeight = stackWindow.getFrame().offsetHeight;
		
		for ( var key in layers ) {
			if ( layers.hasOwnProperty( key ) ) {
				layers[ key ].resize( self.viewWidth, self.viewHeight );
			}
		}
		
		self.overview.redraw();
		
		return;
	}
	
	/**
	 * Get the stack window.
	 */
	this.getWindow = function() { return stackWindow; }
	
	/**
	 * Get the project.
	 */
	this.getProject = function(){ return project; }
	
	/**
	 * Get stack ID.
	 */
	this.getId = function(){ return id; }
	
	
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
	}
	
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
	}
	
	
	/**
	 * Register a tool at this stack.  Unregisters the current tool and then
	 * makes the tool working.
	 */
	this.setTool = function( newTool )
	{
//		if ( typeof tool != "undefined" && tool )
//			tool.unregister();
		tool = newTool;
		if ( typeof tool != "undefined" && tool )
			tool.register( self );
	}

	/** Return the current tool. */
	this.getTool = function()
	{
		return tool;
	}
	
	// initialize
	var self = this;
	if ( !ui ) ui = new UI();
	
	self.id = id;
	
	self.resolution = resolution;
	self.translation = translation;
	self.dimension = dimension;
	
	var tool = null;
	var layers = {};
	
	var max = new Array();
	for ( var i = 0; i < n; ++i )
	{
		max[i] = dimension[i] - 1;
	}
	
	//! estimate the zoom levels
	var tile_size = 256;
	var num_scale_levels = Math.log( dimension[1] / tile_size ) / Math.log( 2 );
	if ( num_scale_levels < 1 )
		num_scale_levels = 1;
	else if ( Math.floor( num_scale_levels ) == num_scale_levels )
		num_scale_levels = Math.floor (num_scale_levels);
	else
		num_scale_levels = Math.floor (num_scale_levels) + 1;
	self.MAX_S = num_scale_levels - 1;


	// TODO: handle broken slices for n dimensions
	//! all possible slices
	self.slices = new Array();
	for ( var i = 0; i < dimension[2]; ++i )
	{
		if ( !skip_planes[ i ] )
			self.slices.push( i );
	}
	
	//-------------------------------------------------------------------------
	
	var transition = new Transition();
	
	// extract the borders of the viewer window from CSS rules
	var viewTop    = parseInt( getPropertyFromCssRules( 3, 0, "top" ) );
	var viewBottom = parseInt( getPropertyFromCssRules( 3, 0, "bottom" ) );
	var viewLeft   = parseInt( getPropertyFromCssRules( 3, 0, "left" ) );
	var viewRight  = parseInt( getPropertyFromCssRules( 3, 0, "right" ) );
	
	var stackWindow = new CMWWindow( title );
	var view = stackWindow.getFrame();

	var viewWidth = stackWindow.getFrame().offsetWidth;
	var viewHeight = stackWindow.getFrame().offsetHeight;
	
	stackWindow.addListener(
		function( callingWindow, signal )
		{
			//alert( signal );
			switch ( signal )
			{
			case CMWWindow.CLOSE:
				project.removeStack( id );
				break;
			case CMWWindow.RESIZE:
				resize();
				redraw();
				break;
			case CMWWindow.FOCUS:
				self.overview.getView().style.zIndex = "6";
				project.setFocusedStack( self );
				break;
			case CMWWindow.BLUR:
				self.overview.getView().style.zIndex = "5";
				if ( tool )
					tool.unregister();
				tool = null;
				window.onresize();
				break;
			}
			return true;
		} );
	
	self.overview = new Overview( self );
	view.appendChild( self.overview.getView() );
	
	var scaleBar = document.createElement( "div" );
	scaleBar.className = "sliceBenchmark";
	scaleBar.appendChild( document.createElement( "p" ) );
	scaleBar.firstChild.appendChild( document.createElement( "span" ) );
	scaleBar.firstChild.firstChild.appendChild( document.createTextNode( "test" ) );
	view.appendChild( scaleBar );
	
	// take care, that all values are within a proper range
    // Declare the x,y,z,s as coordinates in pixels
	//! stack coordinate currently shown at the center pixel of the stack window
	self.pos = new Array( Math.floor( max[0] / 2 ), Math.floor( max[1] / 2 ) );
	for ( var i = 2; i < n; ++i )
		self.pos[i] = 0;
	self.s = self.MAX_S
	self.old_pos = new Array();
	for ( var i = 0; i < n; ++i )
		self.old_pos = -1;
	self.old_s = self.s;
	
	self.scale = 1 / Math.pow( 2, self.s );
	self.old_scale = self.scale;
}

//!< in nanometers
Stack.SCALE_BAR_SIZES = new Array(
			10,
			20,
			25,
			50,
			100,
			200,
			250,
			500,
			1000,
			2000,
			2500,
			5000,
			10000,
			20000,
			25000,
			50000,
			100000,
			200000,
			250000,
			500000,
			1000000,
			2000000,
			2500000,
			5000000,
			10000000,
			20000000,
			25000000,
			50000000,
			100000000,
			200000000,
			250000000,
			500000000,
			1000000000,
			2000000000,
			2500000000,
			5000000000,
			10000000000,
			20000000000,
			25000000000,
			50000000000,
			100000000000,
			200000000000,
			250000000000,
			500000000000 );
Stack.SCALE_BAR_UNITS = new Array(
			"nm",
			unescape( "%u03BCm" ),
			"mm",
			"m" );
