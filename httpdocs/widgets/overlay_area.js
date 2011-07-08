/*
 * An object to handle the draggable dots at the vertices of a polygon.
 */
VertexDot = function (
	xin, // pixel x
	yin, // pixel y 
	r, // inner circle radius
	rs, //circle surround radius
	index, // Area-specific index
	area,  // the Area object that this dot belongs to
  isMidpoint) // is this vertex a midpoint?
{
	this.index = index;
	this.area = area;
	this.isVisible = true;
  this.isMidpoint = isMidpoint;

	var x = xin;
	var y = yin;
	var viewOpacity = 1;
	var surroundOpacity = 0;
	
	this.dotView = area.paper.circle(x, y, r).attr({
		fill: area.fillColor,
		stroke: "none",
		opacity: viewOpacity});
	var dotSurround = area.paper.circle(x, y, rs).attr({
			  fill: "rgb(0,0,0)",
			  stroke: "none",
			  opacity: surroundOpacity
		  });
	dotSurround.vertex = this;
		  
  //Mouse Event Handler Functions
	var start = function() { //handle start of drag
		this.ox = this.attr("cx");
		this.oy = this.attr("cy");
		this.oo = this.vertex.dotView.attr("opacity");
		this.vertex.dotView.attr({opacity: 0.5});
    // Tell the area to ignore click events while dragging, to fix some event propagation weirdness.
		this.vertex.area.setIgnoreClick(true);
	}; 
	var move = function(dx, dy) { //handle drag movement
		this.attr({cx: this.ox + dx, cy: this.oy + dy});
		this.vertex.dotView.attr({cx: this.ox + dx, cy: this.oy + dy});
    this.vertex.syncLocation();
		this.vertex.area.handleDrag(this, this.vertex, false);
	};
	var up = function() { //handle end of drag
		this.vertex.dotView.attr({opacity: this.oo});
		this.vertex.area.setIgnoreClick(false);
    this.vertex.syncLocation();
		this.vertex.area.handleDrag(this, this.vertex, true);
	};
	var over = function() {		//handle mouse over
		this.vertex.dotView.attr({fill: this.vertex.area.highlightColor});
    this.or = this.vertex.dotView.attr("r");
    this.vertex.dotView.attr("r", this.attr("r"));
	};
	var out = function() {  //handle mouse out
		this.vertex.dotView.attr({fill: this.vertex.area.fillColor});
    this.vertex.dotView.attr("r", this.or);
	};
	var click = function(e) { //terminate propagation of click event
    e.stopPropagation();
  };
	
	dotSurround.drag(move, start, up);
	dotSurround.mouseover(over);
	dotSurround.mouseout(out);
  dotSurround.click(click);
  
  // Public Functions
  
  /*
   * Deletes the objects held by this VertexDot
   */
	this.del = function(){
		dotSurround.remove();		
		this.dotView.remove();
    dotSurround = null;
    this.dotView = null;
	};
  
  /*
   * Sets the location of this VertexDot to be the midpoint between two others.
   */
  this.setMidpointLocation = function(v1, v2) {
    if (this.isMidpoint) {
      x = (v1.getX() + v2.getX()) / 2;
      y = (v1.getY() + v2.getY()) / 2;
      this.dotView.attr("cx", x);
      this.dotView.attr("cy", y);
      dotSurround.attr("cx", x);
      dotSurround.attr("cy", y);
    }    
  };
	
  /*
   * Synchronizes the internally-stored location with that of the circle surround
   */
	this.syncLocation = function(){
		x = dotSurround.attr("cx");
		y = dotSurround.attr("cy");
	};
  
  /*
   * Set the visible and surround circle radii.
   */
  this.setRadius = function(
    r, // Visible circle's radius 
    rs // Surround circle's radius
    ) {
    dotSurround.attr({r : rs});
    this.dotView.attr({r : r});
  };
	
  this.getX = function() {
    return x;
  };
  this.getY = function() {
    return y;
  };
	
	this.hide = function(){
		dotSurround.attr({opacity : 0});
		dotView.attr({opacity : 0});
		this.isVisible = false;
		dotSurround.undrag();
	};
	
	this.unhide = function(){
		dotSurround.attr({opacity : surroundOpacity});
		dotView.attr({opacity : viewOpacity});
		this.isVisible = true;
		dotSurround.drag(move, start, up);
	};
	
  
};
 
 
 /*
  * Area handles drawing polygons to a Raphael canvas.
  */
 
Area = function (
id, // unique id for the node from the database
paper, // the raphael paper this area is drawn to
x, // initial x coordinate or coordinates. May be either singleton or array.
y, // ditto, but y
r // the vertex node radius
)
{
    // the database area id
    this.id = id;  
    // type
    this.type = "area";
    // state variable whether this node is already synchronized with the database
    this.needsync = false;
    // The Raphael instance
    this.paper = paper;
    // Vertex dot radius
    this.r = r;
    // Vertex dot surround radius
    this.rcatch = r + 4;
    // Dots Enabled (currently unused)
    this.dotsEnabled = true;
    // Fill color
    this.fillColor = "rgb(255, 128, 0)";
    // Highlight color
    this.highlightColor = "rgb(255, 255, 0)";
    // The SVG path used to represent the polygon
    this.path = paper.path();
    // Used to determine whether we are editting or creating vertices
    this.ignoreClick = false;
    
    /* Edit mode
     * createvertices - appends a new vertex to the end of the list at each click
     * editvertices - drag midpoints to create new vertices
    */
    var mode = "createvertices";
    
    var midx = [], midy = [];

    // An array of VertexDot instances
    var dots = [];
    var mdots = [];
    
    var fillOpacity = 0.2;

    // Arrays used for storing the x,y locations of the vertices
    // Assume that if x is not numeric, then it is an array.
    if (x === parseFloat(x))
    {
       this.x = [x];
       this.y = [y];       
    }
    else
    {      
      this.x = x;
      this.y = y;
    }
  
   
    this.path.attr("fill", this.fillColor);
    this.path.attr("stroke", this.fillColor);
    this.path.attr("fill-opacity", fillOpacity);
    this.path.dblclick(function(){
      this.area.switchMode();
    });
    this.path.area = this;

	// Pushes a new VertexDot onto the array
	this.pushVertexDot = function (x, y, area) {
		vdot = new VertexDot(x, y, this.r, this.rcatch, dots.length, this, false);
		dots.push(vdot);
    };


	this.setIgnoreClick = function(isIt){
		this.ignoreClick = isIt;
	};

    // Add a new x,y location to the end of the polygon
	this.addXY = function (xnew, ynew) {
		if (mode === "createvertices" && !this.ignoreClick) {
			this.x.push(xnew);
			this.y.push(ynew);
			this.pushVertexDot(xnew, ynew);
			this.draw();
		}
	};
   
  // Moves the i'th vertex to the location at x, y. This function is intended to be called
  // from within VertexDot, which handles edit events all its own.
  this.setVertex = function(i, x, y) {
	  if (i < this.x.length)
	  {
		  this.x[i] = x;
		  this.y[i] = y;	
		  this.draw();	  
	  }
  };
  
  this.handleDrag = function(c, v, term) {
    var i = v.index;    
   
    if (!v.isMidpoint) { 
      if (i >= 0 && i < this.x.length) {
        // if i is positive, we're talking about a vertex
        this.x[i] = c.attr("cx");
        this.y[i] = c.attr("cy");
        if (mode === "editvertices") {        
          iLeftMP = i === 0 ? mdots.length - 1 : i - 1;
          iLeftVP = i === 0 ? dots.length - 1 : i - 1;
          iRightVP = i + 1 === dots.length ? 0 : i + 1;
        
          mdots[iLeftMP].setMidpointLocation(dots[iLeftVP], dots[i]);
          mdots[i].setMidpointLocation(dots[i], dots[iRightVP]);
        }
      }
    } else if (i > 0 && i <= this.x.length) {
      var remIndex, j;

      this.x.splice(i, 0, c.attr("cx"));
      this.y.splice(i, 0, c.attr("cy"));

      for (j = i; j < dots.length; j++) {
        dots[j].index = dots[j].index + 1;
        mdots[j].index = mdots[j].index + 1;
      }
      
      dots.splice(i, 0, v);
      
      m1 = this.makeMidpoint(i);
      m2 = this.makeMidpoint(i + 1);
           
      mdots.splice(i - 1, 1, m1, m2);

      v.isMidpoint = false;
      v.setRadius(this.r, this.rcatch);
      
    }
    this.draw();
    
    
  };
  
  this.makeMidpoint = function(i) {
    var l = this.x.length;
    var mx, my;
    if (i > 0 && i < l) {
      mx = (this.x[i] + this.x[i - 1]) / 2;
      my = (this.y[i] + this.y[i - 1]) / 2;
    } else if (i === l) {
      mx = (this.x[l-1] + this.x[0]) / 2;
      my = (this.y[l-1] + this.y[0]) / 2;
    }
    return new VertexDot(mx, my, this.r * 0.75, this.rcatch * 0.75, i, this, true);
  };
  
  this.createMidpoints = function() {    
    var i;
    var l = this.x.length;
    if (l > 1) //if "L" > 1
    {
      for (i = 1; i <= l; i++)
      {
        mdots.push(this.makeMidpoint(i));
//        midx.push(mx);
 //       midy.push(my);
      }
      
//      midx.push(mx);
//      midy.push(my);
//      mdots.push(new VertexDot(mx, my, this.r / 2, this.rcatch / 2, l, this, true));  
    }
    
  };
  
  this.removeMidpoints = function() {
    var i;
    for (i = 0; i < mdots.length; i++) {
      mdots[i].del();
      mdots[i] = null;
    }
    mdots = [];    
  };
  

  // Erases and rebuilds the vertex dot array from scratch, resyncing the dots to the vertices.
  this.resetVertexDots = function() {
    var i;
	  this.deleteVertexDots();
	  for(i = 0; i < this.x.length; i++)
	  {
		  this.pushVertexDot(this.x[i], this.y[i]);		  
	  }
  };
  
  // Removes the vertex dots entirely, rather than just hiding them.
  this.deleteVertexDots = function() {
    var i;
    for (i = 0; i < dots.length; i++)
	  {
		  dots[i].del();
	  }
	  dots = [];
  };
  
  this.getSVGPath = function() {
    var i;
		var pathlist = [];
		
		pathlist.push("M" + this.x[0] + " " + this.y[0]);
		
		for (i = 1; i < this.x.length; i++)
		{
			pathlist.push("L" + this.x[i] + " " + this.y[i]);
		}
		pathlist.push("Z");
		
		return pathlist.join();
	};
    
  
  // Regenerates the SVG code for the polygon, causing it to be redrawn to the screen.
	this.draw = function() {
		this.path.attr("path", this.getSVGPath());
	};
  
  this.switchMode = function() {
    if (mode === "createvertices") {
      mode = "editvertices";
      this.createMidpoints();
    } else {
      mode = "createvertices";
      this.removeMidpoints();
    }    
  };

  if (parseFloat(this.x) === this.x)
  {
    this.pushVertexDot(this.x[0],this.y[0]);
  }
	else
  {
    for (i = 0; i < this.x.length; i++)
    {
      this.pushVertexDot(this.x[i], this.y[i]);
    }
  }
  

};
