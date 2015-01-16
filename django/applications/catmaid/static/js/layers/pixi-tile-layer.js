/* -*- mode: espresso; espresso-indent-level: 2; indent-tabs-mode: nil -*- */
/* vim: set softtabstop=2 shiftwidth=2 tabstop=2 expandtab: */

/**
 *
 */
function PixiTileLayer(
    displayname,
    stack,            //!< reference to the parent stack
    tileWidth,
    tileHeight,
    tileSource,
    visibility,
    opacity,
    showOverview
    )
{
  /**
   * Return friendly name of this layer.
   */
  this.getLayerName = function()
  {
    return self.displayname;
  };

  /**
   * initialise the tiles array
   */
  var initTiles = function( rows, cols )
  {
    if (!batchContainer) {
      batchContainer = new PIXI.DisplayObjectContainer();
      stage.addChild(batchContainer);
    } else batchContainer.removeChildren();

    var graphic = new PIXI.Graphics();
    graphic.beginFill(0xFFFFFF,0);
    graphic.drawRect(0,0,tileWidth,tileHeight);
    graphic.endFill();
    var emptyTex = graphic.generateTexture(false);

    tiles = [];

    for ( var i = 0; i < rows; ++i )
    {
      tiles[ i ] = [];
      tiles_buf[i] = [];

      for ( var j = 0; j < cols; ++j )
      {
        tiles[ i ][ j ] = new PIXI.Sprite(emptyTex);
        batchContainer.addChild(tiles[i][j]);
        tiles[i][j].position.x = j * tileWidth;
        tiles[i][j].position.y = i * tileHeight;

        tiles_buf[i][j] = false;
      }
    }

    return;
  };

  /**
   * align and update the tiles to be ( x, y ) in the image center
   */
  this.redraw = function(completionCallback)
  {
    var pixelPos = [ stack.x, stack.y, stack.z ];
    var tileBaseName = getTileBaseName( pixelPos );

    var zoom = stack.s;
    var mag = 1.0;
    var artificialZoom = false;
    /* If the zoom is negative we zoom in digitally. For this
     * we take the zero zoom level and adjust the tile properties.
     * This way we let the browser do the zooming work.
     */
    if (zoom < 0 || zoom % 1 !== 0) {
      artificialZoom = true;
      /* For nonintegral zoom levels the ceiling is used to select
       * source image zoom level. While using the floor would allow
       * better image quality, it would requiring dynamically
       * increasing the number of tiles to fill the viewport since
       * in that case effectiveTileWidth < tileWidth.
       */
      zoom = Math.max(0, Math.ceil(zoom));
      /* Magnification is positive for digital zoom beyond image
       * resolution and negative for non-integral zooms within
       * image resolution.
       */
      mag = Math.pow(2, zoom - stack.s);
    }

    var effectiveTileWidth = tileWidth * mag;
    var effectiveTileHeight = tileHeight * mag;

    var fr = Math.floor( stack.yc / effectiveTileHeight );
    var fc = Math.floor( stack.xc / effectiveTileWidth );

    var xd = 0;
    var yd = 0;

    // If panning only (no scaling, no browsing through z)
    if ( stack.z == stack.old_z && stack.s == stack.old_s )
    {
      var old_fr = Math.floor( stack.old_yc / effectiveTileHeight );
      var old_fc = Math.floor( stack.old_xc / effectiveTileWidth );

      // Compute panning in X and Y
      xd = fc - old_fc;
      yd = fr - old_fr;

      // re-order the tiles array on demand
      if ( xd < 0 )
      {
        // Panning to the left:
        // Move the last column of tiles to the first column
        for ( var i = tiles.length - 1; i >= 0; --i )
        {
          for (var j = tiles[i].length - 1; j >= 1; --j){
            tiles[i][j].setTexture(tiles[i][j-1].texture);
          }
          tiles[i][0].visible = false;
        }
      }
      else if ( xd > 0 )
      {
        // Panning to the right:
        // Move the first column of tiles to the last column
        for ( var i = tiles.length - 1; i >= 0; --i )
        {
          for (var j = 0; j < tiles[i].length - 1; ++j){
            tiles[i][j].setTexture(tiles[i][j+1].texture);
          }
          tiles[i][tiles[i].length - 1].visible = false;
        }
      }

      if ( yd < 0 )
      {
        // Panning to the top:
        // Move the last row of tiles to the first row
        for ( var i = tiles.length - 1; i >= 1; --i )
        {
          for (var j = tiles[i].length - 1; j >= 0; --j){
            tiles[i][j].setTexture(tiles[i-1][j].texture);
          }
        }
      }
      else if ( yd > 0 )
      {
        // Panning to the bottom:
        // Move the first row of tiles to the last row
        for ( var i = 0; i < tiles.length - 1; ++i )
        {
          for (var j = tiles[i].length - 1; j >= 0; --j){
            tiles[i][j].setTexture(tiles[i+1][j].texture);
          }
        }
      }
    }

    // Adjust the last tile in a row or column to be visible rather than hidden.
    // Must run when changing scale, or when changing the size of the canvas window.
    // Considering how inexpensive it is, it is made to run always.
    if (artificialZoom)
    {
      // Adjust last tile index to display to the one intersecting the bottom right
      // of the field of view. The purpose: to hide images beyond the stack edges.
      // Notice that we add the panning xd, yd as well (which is already in tile units).
      LAST_XT = Math.floor((stack.x * stack.scale + stack.viewWidth) / effectiveTileWidth) + xd;
      LAST_YT = Math.floor((stack.y * stack.scale + stack.viewHeight) / effectiveTileHeight) + yd;

      // Clamp last tile coordinates within the slice edges.
      LAST_XT = Math.min(LAST_XT, Math.floor((stack.dimension.x * Math.pow(2, -zoom) - 1) / tileWidth));
      LAST_YT = Math.min(LAST_YT, Math.floor((stack.dimension.y * Math.pow(2, -zoom) - 1) / tileHeight));
    }
    else
    {
      LAST_XT = Math.floor( ( stack.dimension.x * stack.scale - 1 ) / tileWidth );
      LAST_YT = Math.floor( ( stack.dimension.y * stack.scale - 1 ) / tileHeight );
    }

    var top;
    var left;

    if ( stack.yc >= 0 )
      top  = -( stack.yc % effectiveTileHeight );
    else
      top  = -( ( stack.yc + 1 ) % effectiveTileHeight ) - effectiveTileHeight + 1;
    if ( stack.xc >= 0 )
      left = -( stack.xc % effectiveTileWidth );
    else
      left = -( ( stack.xc + 1 ) % effectiveTileWidth ) - effectiveTileWidth + 1;

    batchContainer.position.x = left;
    batchContainer.position.y = top;
    batchContainer.scale.x = mag;
    batchContainer.scale.y = mag;

    // update the images sources
    for ( var i = 0; i < tiles.length; ++i )
    {
      var r = fr + i;
      for ( var j = 0; j < tiles[ 0 ].length; ++j )
      {
        var c = fc + j;

        if ( r >= 0 && c >= 0 && r <= LAST_YT && c <= LAST_XT )
        {
          var source = self.tileSource.getTileURL( project, stack,
            tileBaseName, tileWidth, tileHeight, c, r, zoom);

          var tile = tiles[i][j];
          if (source != tile.texture.baseTexture.imageUrl) {
            var loader = new PIXI.ImageLoader(source);
            tiles_buf[i][j] = loader;
            loader.on('loaded', this.checkBuffer.bind(this));
            loader.load();
          } else tile.visible = true;
        } else tiles[i][j].visible = false;
      }
    }

    if (stack.z == stack.old_z && zoom == Math.max(0, Math.ceil(stack.old_s)))
      renderer.render(stage);

    if (this.isBuffering())
      loadBufferTimeout = window.setTimeout(this.loadBuffer.bind(this), 3000);

    if (typeof completionCallback !== "undefined") {
      completionCallback();
    }

    return 2;
  };

  this.checkBuffer = function () {
    if (!this.isBuffering()) this.loadBuffer();
  };

  this.isBuffering = function () {
    return tiles_buf.some(function (r) { return r.some( function (c) {
        return c && !c.texture.valid; }); });
  };

  this.loadBuffer = function () {
    window.clearTimeout(loadBufferTimeout);

    for (var i = 0; i < tiles.length; ++i) {
      for (var j = 0; j < tiles[ 0 ].length; ++j) {
        if (tiles_buf[i][j]) {
          tiles[i][j].setTexture(tiles_buf[i][j].texture);
          tiles[i][j].visible = true;
          tiles_buf[i][j] = false;
        }
      }
    }

    renderer.render(stage);
  };

  this.resize = function( width, height )
  {
    if (width == renderer.width && height == renderer.height) return;

    renderer.resize(width, height);
    var rows = Math.floor( height / tileHeight ) + 2;
    var cols = Math.floor( width / tileWidth ) + 2;
    initTiles( rows, cols );
    self.redraw();
  };

  /**
   * Get the width of an image tile.
   */
  this.getTileWidth = function(){ return tileWidth; };

  /**
   * Get the height of an image tile.
   */
  this.getTileHeight = function(){ return tileHeight; };

  /**
   * Get the stack.
   */
  this.getStack = function(){ return stack; };

  /* Set opacity in the range from 0 to 1 */
  this.setOpacity = function( val )
  {
    tilesContainer.style.opacity = val+"";
    self.opacity = val;
    if(val < 0.02) {
      if(self.visible)
        self.isolateTileLayer();
    } else {
      if(!self.visible)
        self.reattachTileLayer();
    }
  };

  this.updateOpacity = function() {
    self.setOpacity( opacity );
  };

  this.getOpacity = function()
  {
    return self.opacity;
  };

  this.isolateTileLayer = function()
  {
    stack.getView().removeChild( tilesContainer );
    self.visible = false;
  };

  this.reattachTileLayer = function()
  {
    stack.getView().appendChild( tilesContainer );
    self.visible = true;
  };

  // initialise
  var self = this;

  self.displayname = displayname;
  self.opacity = opacity; // in the range [0,1]
  self.visible = visibility;
  self.tileSource = tileSource;

  /* Contains all tiles in a 2d-array */
  var tiles = [];
  var tiles_buf = [];

  var batchContainer = null;
  var renderer = new PIXI.autoDetectRenderer(stack.getView().clientWidth, stack.getView().clientHeight);
  self.stage = new PIXI.Stage(0x000000);
  var stage = self.stage;

  var tilesContainer = renderer.view;
  tilesContainer.className = "sliceTiles";

  if( self.visible )
    stack.getView().appendChild( tilesContainer );

  var loadBufferTimeout = null;

  var LAST_XT = Math.floor( ( stack.dimension.x * stack.scale - 1 ) / tileWidth );
  var LAST_YT = Math.floor( ( stack.dimension.y * stack.scale - 1 ) / tileHeight );

  if( showOverview ) {
    // Initialize the OverviewLayer on the bottom-right with the correct
    // path to the small thumbnail images depending on the tile source type
    // This is only run for the TileLayer which usually holds the primary
    // raw data, and not for additional overlay layers. Overlay layers are
    // currently not shown with a small image.
    var overviewLayer = tileSource.getOverviewLayer( this );
  }


}
