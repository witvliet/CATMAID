/*
 * An open area object. Used for a new area in-progress.
 */
VertexDot = function (
	xin,
	yin,
	r,
	rs,
	index,
	area)
{
	this.index = index;
	this.area = area;
	this.isVisible = true;

	var x = xin;
	var y = yin;
	var viewOpacity = 1;
	var surroundOpacity = 0.1;
	
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
		  
	var start = function() {
		this.ox = this.attr("cx");
		this.oy = this.attr("cy");
		this.oo = this.vertex.dotView.attr("opacity");
		this.vertex.dotView.attr({opacity: .5});
		this.vertex.area.dotDragging(true);
	}; 
	var move = function(dx, dy) {
		this.attr({cx: this.ox + dx, cy: this.oy + dy});
		this.vertex.dotView.attr({cx: this.ox + dx, cy: this.oy + dy});
		this.vertex.updateLocation();
	};
	var up = function() {
		this.vertex.dotView.attr({opacity: this.oo});
		this.vertex.area.dotDragging(false);
		this.vertex.updateLocation();
	};
	var over = function() {		
		this.vertex.dotView.attr({fill: this.vertex.area.highlightColor});
	};
	var out = function() {
		this.vertex.dotView.attr({fill: this.vertex.area.fillColor});
	};
	
	
	dotSurround.drag(move, start, up);
	dotSurround.mouseover(over);
	dotSurround.mouseout(out);
	
	this.del = function(){
		dotSurround.remove();		
		this.dotView.remove();
	};
	
	this.updateLocation = function(){
		x = dotSurround.attr("cx");
		y = dotSurround.attr("cy");
		this.area.setVertex(this.index, x, y);
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
	}
	
};
 
 
Area = function (
id, // unique id for the node from the database
paper, // the raphael paper this area is drawn to
x, // the x coordinate of the first vertex
y, // the y coordinate of the first vertex
r // the vertex node radius
)
{
    // the database area id
    this.id = id;  
    this.type = "area";

    // state variable whether this node is already synchronized with the database
    this.needsync = false;

    // Arrays used for storing the x,y locations of the vertices
    this.x = [x];
    this.y = [y];
    // The Raphael instance
    this.paper = paper;
    // Vertex dot radius
    this.r = r;
    // Vertex dot surround radius
    this.rcatch = r + 4;
    // Dots Enabled (currently unused)
    this.dotsEnabled = "true";  
    // Fill color
    this.fillColor = "rgb(255, 128, 0)";
    // Highlight color
    this.highlightColor = "rgb(255, 255, 0)";
    // The SVG path used to represent the polygon
    this.path = paper.path();
    // Used to determine whether we are editting or creating vertices
    this.isDragging = false;

    // An array of VertexDot instances
    var dots = [];
    
    var fillOpacity = 0.2;
  
   
    this.path.attr("fill", this.fillColor)
    this.path.attr("stroke", this.fillColor);
    this.path.attr("fill-opacity", fillOpacity);

	// Pushes a new VertexDot onto the array
	this.pushVertexDot = function (x, y, area) {
		vdot = new VertexDot(x, y, this.r, this.rcatch, dots.length, this);
		dots.push(vdot);
    };


	this.dotDragging = function(isIt){
		this.isDragging = isIt;
	};

    // Add a new x,y location to the end of the polygon
	this.addXY = function (xnew, ynew) {
		if (!this.isDragging) {
			this.x.push(xnew)
			this.y.push(ynew);
			this.pushVertexDot(xnew, ynew);
			this.draw();
		};
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

  // Erases and rebuilds the vertex dot array from scratch, resyncing the dots to the vertices.
  this.resetVertexDots = function() {
	  this.deleteVertexDots();
	  for(var i = 0; i < this.x.length; i++)
	  {
		  this.pushVertexDot(this.x[i], this.y[i]);		  
	  }
  };
  
  // Removes the vertex dots entirely, rather than just hiding them.
  this.deleteVertexDots = function() {
  	  for (var i = 0; i < dots.length; i++)
	  {
		  dots[i].del();
	  }
	  dots = [];
  };
  
    this.getSVGPath = function() {
		var pathlist = [];
		
		pathlist.push("M" + this.x[0] + " " + this.y[0]);
		
		for (var i = 1; i < this.x.length; i++)
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

	this.pushVertexDot(x,y);
  

};
