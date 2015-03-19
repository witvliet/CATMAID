/* -*- mode: espresso; espresso-indent-level: 2; indent-tabs-mode: nil -*- */

/**
 * Get the part of the tile name that consists of dimensions z, t, ...
 * For a 3D stack this will return 'z/', for a 4D stack 't/z/', etc.
 *
 * @param pixelPos pixel position of the stack [x, y, z, t, ...]
 */
function getTileBaseName(pixelPos) {
  var n = pixelPos.length;
  var dir = '';
  for (var i = n - 1; i > 1; --i) {
    dir += pixelPos[i] + '/';
  }
  return dir;
}

/**
 * Displays a grid of tiles from an image stack.
 * @constructor
 * @param {string}  displayname  Name displayed in window controls.
 * @param {Stack}   stack        Image stack from which to draw tiles.
 * @param {number}  tileWidth    Width of tile images in pixels.
 * @param {number}  tileHeight   Height of tile images in pixel.
 * @param {Object}  tileSource   Tile source for generating image URLs.
 * @param {boolean} visibility   Whether the tile layer is initially visible.
 * @param {number}  opacity      Opacity to draw the layer.
 * @param {boolean} showOverview Whether to show a "minimap" overview of the
 *                               stack.
 */
function TileLayer(
    displayname,
    stack,
    tileWidth,
    tileHeight,
    tileSource,
    visibility,
    opacity,
    showOverview) {
  this.displayname = displayname;
  this.stack = stack;
  this.tileWidth = tileWidth;
  this.tileHeight = tileHeight;
  this.tileSource = tileSource;
  this.opacity = opacity; // in the range [0,1]
  this.visible = visibility;

  /** @type {[[Element]]} Contains all tiles in a 2D toroidal array */
  this._tiles = [];
  /** @type {number} Current origin row in the tiles array. */
  this._tileOrigR = 0;
  /** @type {number} Current origin column in the tiles array. */
  this._tileOrigC = 0;
  this._tilesBuffer = [];
  this._buffering = false;
  this._swapBuffersTimeout = null;

  this.tilesContainer = document.createElement('div');
  this.tilesContainer.className = 'sliceTiles';

  if (this.visible)
    stack.getView().appendChild(this.tilesContainer);

  if (showOverview) {
    // Initialize the OverviewLayer on the bottom-right with the correct
    // path to the small thumbnail images depending on the tile source type
    // This is only run for the TileLayer which usually holds the primary
    // raw data, and not for additional overlay layers. Overlay layers are
    // currently not shown with a small image.
    this.overviewLayer = tileSource.getOverviewLayer(this);
  }
}

/**
 * Return friendly name of this layer.
 */
TileLayer.prototype.getLayerName = function () {
  return this.displayname;
};

/**
 * Initialise the tiles array and buffer.
 */
TileLayer.prototype._initTiles = function (rows, cols) {
  while (this.tilesContainer.firstChild)
    this.tilesContainer.removeChild(this.tilesContainer.firstChild);

  var tileOnload = function () {
    if (this.alt === 'h') return;
    this.style.visibility = 'visible';
    this.alt = 'l'; // Set a flag to indicate this image has loaded
  };

  this._tiles = [];

  this._tilesBuffer = [];

  this._tileOrigR = 0;
  this._tileOrigC = 0;

  for (var i = 0; i < rows; ++i) {
    this._tiles[i] = [];
    this._tilesBuffer[i] = [];
    for (var j = 0; j < cols; ++j) {
      var tile = document.createElement( 'img' );
      // The alt attribute of these and the buffer's images is abused
      // to indicate states for buffering resilience: empty for
      // loading an image, 'l' for a loaded image, and 'h' for hidden.
      tile.alt = '';
      tile.style.visibility = 'hidden';
      tile.onload = tileOnload;
      this._tiles[i][j] = tile;

      this._tilesBuffer[i][j] = document.createElement('img');
      this._tilesBuffer[i][j].alt = '';
      this._tilesBuffer[i][j].visibility = 'hidden';

      this.tilesContainer.appendChild(tile);
    }
  }
};

TileLayer.prototype.rowTransform = function (r) {
  var rows = this._tiles.length;
  return ((r % rows) + rows + this._tileOrigR) % rows;
};

TileLayer.prototype.colTransform = function (c) {
  var cols = this._tiles[0].length;
  return ((c % cols) + cols + this._tileOrigC) % cols;
};

/**
 * Update and draw the tile grid based on the current stack position and scale.
 */
TileLayer.prototype.redraw = function (completionCallback) {
  var pixelPos = [this.stack.x, this.stack.y, this.stack.z];
  var tileBaseName = getTileBaseName(pixelPos);

  var tileInfo = this.tilesForLocation(this.stack.xc, this.stack.yc, this.stack.z, this.stack.s);

  var effectiveTileWidth = this.tileWidth * tileInfo.mag;
  var effectiveTileHeight = this.tileHeight * tileInfo.mag;

  var rows = this._tiles.length, cols = this._tiles[0].length;

  // If panning only (no scaling, no browsing through z)
  if (this.stack.z == this.stack.old_z && this.stack.s == this.stack.old_s)
  {
    var old_fr = Math.floor(this.stack.old_yc / effectiveTileHeight);
    var old_fc = Math.floor(this.stack.old_xc / effectiveTileWidth);

    // Compute panning in X and Y
    var xd = tileInfo.first_col - old_fc;
    var yd = tileInfo.first_row - old_fr;

    // Hide wrapped tiles. Here it is assumed abs({xd|yd}) <= 1, i.e.,
    // it is impossible to pan more than one tile in a single redraw.
    if (xd !== 0) {
      // Panning to the left or right:
      // hide the former last or first column of tiles, respectively.
      var col = this.colTransform(xd < 0 ? -1 : 0);
      for (var i = rows - 1; i >= 0; --i)
        this._tiles[i][col].style.visibility = 'hidden';
    }

    if (yd !== 0) {
      // Panning to the top or bottom:
      // hide the former last or first row of tiles, respectively.
      var row = this.rowTransform(yd < 0 ? -1 : 0);
      for (var j = cols - 1; j >= 0; --j)
        this._tiles[row][j].style.visibility = 'hidden';
    }

    // Update the toroidal origin in the tiles array
    this._tileOrigR = this.rowTransform(yd); //(tileOrigR + yd + tiles.length) % tiles.length;
    this._tileOrigC = this.colTransform(xd); //(tileOrigC + xd + tiles[0].length) % tiles[0].length;
  }

  var top;
  var left;

  if (this.stack.yc >= 0)
    top  = -(this.stack.yc % effectiveTileHeight);
  else
    top  = -((this.stack.yc + 1) % effectiveTileHeight) - effectiveTileHeight + 1;
  if (this.stack.xc >= 0)
    left = -(this.stack.xc % effectiveTileWidth);
  else
    left = -((this.stack.xc + 1) % effectiveTileWidth) - effectiveTileWidth + 1;

  var t = top;
  var l = left;

  // If zooming or changing z sections (not panning), attempt to preload
  // images to paint at once (but let regular code run for new stacks.)
  this._buffering = this.stack.z !== this.stack.old_z ||
      tileInfo.zoom !== Math.max(0, Math.ceil(this.stack.old_s));

  var to_buffer =
      (tileInfo.last_col - Math.max(0, tileInfo.first_col) + 1) *
      (tileInfo.last_row - Math.max(0, tileInfo.first_row) + 1);
  var buffered = 0;

  // Set a timeout for slow connections to swap in the buffer whether or
  // not it has loaded.
  if (this._buffering) {
    window.clearTimeout(this.swapBuffersTimeout);
    this.swapBuffersTimeout = window.setTimeout(this._swapBuffers.bind(this), 3000);
  }

  // Callback to deal with buffered image loading. Calls swapBuffers once
  // all requested images have been loaded in the tile buffer.
  var self = this;
  function bufferLoadDeferred() {
    return function () {
      if (!self._buffering || this.alt === 'h') return;
      buffered = buffered + 1;
      this.alt = 'l';
      if (buffered === to_buffer) {
        window.clearTimeout(self.swapBuffersTimeout);
        self._swapBuffers();
      }
    };
  }

  var nextL, nextT, seamRow;

  // Update tiles (or the tile buffer).
  for (var i = this._tileOrigR, ti = 0; ti < rows; ++ti, i = (i+1) % rows) {
    var r = tileInfo.first_row + ti;

    nextT = t + effectiveTileHeight;
    seamRow = Math.round(nextT) - nextT > 0;

    for (var j = this._tileOrigC, tj = 0; tj < cols; ++tj, j = (j+1) % cols) {
      var c = tileInfo.first_col + tj;
      var tile = this._buffering ? this._tilesBuffer[i][j] : this._tiles[i][j];

      nextL = l + effectiveTileWidth;

      if (c >= 0 && c <= tileInfo.last_col &&
          r >= 0 && r <= tileInfo.last_row) {
        var source = this.tileSource.getTileURL(project, this.stack,
            tileBaseName, this.tileWidth, this.tileHeight,
            c, r, tileInfo.zoom);

        tile.style.top = t + 'px';
        tile.style.left = l + 'px';

        // To prevent tile seams when the browser is going to round the
        // edge of the next column up a pixel, grow the width of this
        // column slightly to fill the gap
        if (Math.round(nextL) - nextL > 0) {
          tile.style.width = Math.ceil(effectiveTileWidth) + 'px';
        } else {
          tile.style.width = effectiveTileWidth + 'px';
        }

        // As above, prevent tile seams when the next row will round up
        if (seamRow) {
          tile.style.height = Math.ceil(effectiveTileHeight) + 'px';
        } else {
          tile.style.height = effectiveTileHeight + 'px';
        }

        if (tile.src === source) {
          if (tile.alt === 'h') tile.alt = 'l';
          if (this._buffering) {
            bufferLoadDeferred().call(tile);
          }
          // If a tile was hidden earlier, but we now wish to
          // show it again and it happens to have the same src,
          // Chrome will not fire the onload event if we set src.
          // Instead check the flag we set in alt when loaded.
          else if (tile.alt) {
            tile.style.visibility = 'visible';
          }
        } else {
          tile.alt = ''; // Mark that the correct image for this
                   // tile has not yet loaded.
          if (this._buffering) tile.onload = bufferLoadDeferred();
          tile.src = source;
        }
      } else {
        tile.alt = 'h';
        tile.style.visibility = 'hidden';
      }

      l = nextL;
    }

    l = left;
    t = nextT;
  }

  if (typeof completionCallback !== 'undefined') {
    completionCallback();
  }
};

/**
 * Helper function to swap source images from tilesBuffer into tiles.
 */
TileLayer.prototype._swapBuffers = function () {
  if (!this._buffering) return;
  this._buffering = false; // If timeout, prevent load callbacks from calling
  var rows = this._tiles.length, cols = this._tiles[0].length;
  for (var i = 0; i < rows; ++i) {
    for (var j = 0; j < cols; ++j) {
      var tile = this._tiles[i][j];
      var buf = this._tilesBuffer[i][j];

      tile.alt = buf.alt;
      tile.style.visibility = (buf.alt === 'h') ? 'hidden' : 'visible';
      tile.style.width = buf.style.width;
      tile.style.height = buf.style.height;
      tile.style.top = buf.style.top;
      tile.style.left = buf.style.left;
      tile.src = buf.src;
    }
  }
};

/**
 * Resize (if necessary) the tile grid to cover a view of a specified size.
 * @param  {number} width  Width of the view in pixels.
 * @param  {number} height Height of the view in pixels.
 */
TileLayer.prototype.resize = function (width, height) {
  var rows = Math.ceil(height / this.tileHeight) + 1;
  var cols = Math.ceil(width / this.tileWidth) + 1;
  if (this._tiles.length === 0 || this._tiles.length !== rows || this._tiles[0].length !== cols)
    this._initTiles(rows, cols);
  this.redraw();
};

/**
 * Loads tiles at specified indices, but does not display them, so that
 * they are cached for future viewing.
 * @param  {[[]]}                     tileIndices      an array of tile
 *                                                     indices like:
 *                                                     [c, r, z, s]
 * @param  {function(number, number)} progressCallback
 */
TileLayer.prototype.cacheTiles = function (tileIndices, progressCallback, cachedCounter, loaders) {
  if (typeof cachedCounter === 'undefined') cachedCounter = 0;

  // Truncate request to no more than 3000 tiles.
  if (tileIndices.length > 3000) tileIndices.splice(3000);

  progressCallback(tileIndices.length, cachedCounter);
  // Check if the queue is empty
  if (0 === tileIndices.length) return;

  var BATCH_SIZE = 16;
  var numLoaders = Math.min(BATCH_SIZE, tileIndices.length);
  var loaded = 0;

  if (typeof loaders === 'undefined') {
    loaders = [];
    for (var i = 0; i < numLoaders; ++i)
      loaders[i] = new Image();
  }

  var self = this;
  tileIndices.splice(0, numLoaders).forEach(function (tileInd, i) {
    var img = loaders[i];
    img.onload = img.onerror = function () {
      loaded += 1;
      if (loaded >= numLoaders)
        self.cacheTiles(tileIndices, progressCallback, cachedCounter + numLoaders, loaders);
    };
    img.src = self.tileSource.getTileURL(
        project, self.stack,
        getTileBaseName(tileInd.slice(0, 3)),
        self.tileWidth, self.tileHeight,
        tileInd[0], tileInd[1], tileInd[3]);
  });
};

/**
 * Loads tiles for views centered at specified project locations, but does
 * not display them, so that they are cached for future viewing.
 * @param  {[[]]}                     locations        an array of project
 *                                                     coords like:
 *                                                     [x, y, z]
 * @param  {function(number, number)} progressCallback
 */
TileLayer.prototype.cacheLocations = function (locations, progressCallback) {
  var s = this.stack.s;
  var self = this;

  var tileIndices = locations.reduce(function (tileInds, loc) {
    var tileInfo = self.tilesForLocation(
        // Convert project coords to scaled stack coords of a view corner.
        loc[0] * self.stack.scale / self.stack.resolution.x - self.stack.viewWidth / 2,
        loc[1] * self.stack.scale / self.stack.resolution.y - self.stack.viewHeight / 2,
        Math.floor(loc[2] / self.stack.resolution.z),
        s);
    for (var i = tileInfo.first_col; i <= tileInfo.last_col; ++i)
      for (var j = tileInfo.first_row; j <= tileInfo.last_row; ++j)
        tileInds.push([i, j, tileInfo.z, tileInfo.zoom]);

    return tileInds;
  }, []);

  this.cacheTiles(tileIndices, progressCallback);
};

/**
 * Generate bounds on the tile indices for a specified view using the current
 * stack view size.
 * @param  {number} xc Left view origin in scaled stack coordinates.
 * @param  {number} yc Top view origin in scaled stack coordinates.
 * @param  {number} z  Stack section number.
 * @param  {number} s  Stack scale.
 * @return {Object}    Object containing information sufficient to generate
 *                     tile indicies for all tiles in the requested view.
 */
TileLayer.prototype.tilesForLocation = function (xc, yc, z, s) {
  var zoom = s;
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
    mag = Math.pow(2, zoom - s);
  }

  var effectiveTileWidth = this.tileWidth * mag;
  var effectiveTileHeight = this.tileHeight * mag;

  var fr = Math.floor(yc / effectiveTileHeight);
  var fc = Math.floor(xc / effectiveTileWidth);

  var lr, lc;

  // Adjust last tile index to display to the one intersecting the bottom right
  // of the field of view. The purpose: to hide images beyond the stack edges.
  // Notice that we add the panning xd, yd as well (which is already in tile units).
  lc = Math.floor((xc + this.stack.viewWidth) / effectiveTileWidth);
  lr = Math.floor((yc + this.stack.viewHeight) / effectiveTileHeight);

  // Clamp last tile coordinates within the slice edges.
  lc = Math.min(lc, Math.floor((this.stack.dimension.x * Math.pow(2, -zoom) - 1) / this.tileWidth));
  lr = Math.min(lr, Math.floor((this.stack.dimension.y * Math.pow(2, -zoom) - 1) / this.tileHeight));

  return {
    first_row: fr,
    first_col: fc,
    last_row:  lr,
    last_col:  lc,
    z:         z,
    zoom:      zoom,
    mag:       mag
  };
};

/**
 * Get the stack.
 */
TileLayer.prototype.getStack = function () { return this.stack; };

/**
 * Set opacity in the range from 0 to 1.
 * @param {number} val New opacity.
 */
TileLayer.prototype.setOpacity = function (val) {
  this.tilesContainer.style.opacity = val + '';
  this.opacity = val;
  if (val < 0.02) {
    if (this.visible)
      this.isolateTileLayer();
  } else {
    if (!this.visible)
      this.reattachTileLayer();
  }
};

/**
 * Get the layer opacity.
 */
TileLayer.prototype.getOpacity = function () {
  return this.opacity;
};

/**
 * Remove tile elements from DOM.
 */
TileLayer.prototype.isolateTileLayer = function () {
  this.stack.getView().removeChild(this.tilesContainer);
  this.visible = false;
};

/**
 * Attach tile elements to the DOM.
 */
TileLayer.prototype.reattachTileLayer = function ()
{
  this.stack.getView().appendChild(this.tilesContainer);
  this.visible = true;
};
