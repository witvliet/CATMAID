/**
 * selector.js
 *
 * requirements:
 *	 tools.js
 *	 ui.js
 *	 slider.js
 *   stack.js
 */

/**
 */

/**
 * Selector tool.  Moves the stack around and should serve as a general selector
 * of any annotated structure.
 */
function Selector()
{
	var self = this;
	var stack = null;

	if ( !ui ) ui = new UI();

	//! mouse catcher
	var mouseCatcher = document.createElement( "div" );
	mouseCatcher.className = "sliceMouseCatcher";
	mouseCatcher.style.cursor = "default";
	
	this.resize = function( width, height )
	{
		mouseCatcher.style.width = width + "px";
		mouseCatcher.style.height = height + "px";
		return;
	}
	
	var onmousemove =
	{
		pos : function( e )
		{
			var m = ui.getMouse( e );
			if ( m )
			{
				var pos_x = stack.translation[0] + ( stack.pos[0] + ( m.offsetX - stack.viewWidth / 2 ) / stack.scale ) * stack.resolution[0];
				var pos_y = stack.translation[1] + ( stack.pos[1] + ( m.offsetY - stack.viewHeight / 2 ) / stack.scale ) * stack.resolution[1];
				statusBar.replaceLast( "[" + pos_x.toFixed( 3 ) + ", " + pos_y.toFixed( 3 ) + "]" );
			}
			return false;
		},
		move : function( e )
		{
			var posp = stack.pos.slice(0);
			posp[0] -= ui.diffX / stack.scale;
			posp[1] -= ui.diffY / stack.scale;
			stack.moveToPixel( posp, stack.s );
			return false;
		}
	};
	
	var onmouseup = function( e )
	{
		switch ( ui.getMouseButton( e ) )
		{
		case 1:
			break;
		case 2:
			ui.releaseEvents()
			ui.removeEvent( "onmousemove", onmousemove.move );
			ui.removeEvent( "onmouseup", onmouseup );
			break;
		case 3:
			break;
		}
		return false;
	};
	
	var onmousedown = function( e )
	{
		switch ( ui.getMouseButton( e ) )
		{
		case 1:
			// select something ...
			break;
		case 2:			
			ui.registerEvent( "onmousemove", onmousemove.move );
			ui.registerEvent( "onmouseup", onmouseup );
			ui.catchEvents( "move" );
			ui.onmousedown( e );
			ui.catchFocus();
			break;
		case 3:
			break;
		}
		return false;
	};
	
	var onmousewheel = function( e )
	{
		var posp = stack.pos.slice(0);
		var xp = posp[0];
		var yp = posp[1];
		var m = ui.getMouse( e );
		var w = ui.getMouseWheel( e );
		if ( m )
		{
			xp = m.offsetX - stack.viewWidth / 2;
			yp = m.offsetY - stack.viewHeight / 2;
			//statusBar.replaceLast( ( m.offsetX - viewWidth / 2 ) + " " + ( m.offsetY - viewHeight / 2 ) );
		}
		if ( w )
		{
			if ( w > 0 )
			{
				if ( stack.s < stack.MAX_S )
				{
					posp[0] -= Math.floor( xp / stack.scale );
					posp[1] -= Math.floor( yp / stack.scale );
					stack.moveToPixel( posp, stack.s + 1 );
				}
			}
			else
			{
				if ( stack.s > 0 )
				{
					var ns = stack.scale * 2;
					posp[0] += Math.floor( xp / ns );
					posp[1] += Math.floor( yp / ns );
					stack.moveToPixel( posp, stack.s - 1 );
				}
			}
		}
		return false;
	}
	
	/**
	 * install this tool in a stack.
	 * register all GUI control elements and event handlers
	 */
	this.register = function( parentStack )
	{
		document.getElementById( "edit_button_select" ).className = "button_active";
		
		stack = parentStack;

		mouseCatcher.onmousedown = onmousedown;
		try
		{
			mouseCatcher.addEventListener( "DOMMouseScroll", onmousewheel, false );
			/* Webkit takes the event but does not understand it ... */
			mouseCatcher.addEventListener( "mousewheel", onmousewheel, false );
		}
		catch ( error )
		{
			try
			{
				mouseCatcher.onmousewheel = onmousewheel;
			}
			catch ( error ) {}
		}
		
		stack.getView().appendChild( mouseCatcher );

		return;
	}
	
	/**
	 * unregister all stack related mouse and keyboard controls
	 */
	this.unregister = function()
	{
		if ( stack && mouseCatcher.parentNode == stack.getView() )
			stack.getView().removeChild( mouseCatcher );
		return;
	}
	
	/**
	 * unregister all project related GUI control connections and event
	 * handlers, toggle off tool activity signals (like buttons)
	 */
	this.destroy = function()
	{
		self.unregister();
		document.getElementById( "edit_button_select" ).className = "button";
		stack = null;
		return;
	}
}

