<?php

include_once( 'errors.inc.php' );
include_once( 'db.pg.class.php' );
include_once( 'session.class.php' );
include_once( 'tools.inc.php' );
include_once( 'json.inc.php' );

$db =& getDB();
$ses =& getSession();

$pid = isset( $_REQUEST[ 'pid' ] ) ? intval( $_REQUEST[ 'pid' ] ) : 0;
$uid = $ses->isSessionValid() ? $ses->getId() : 0;

$z = isset( $_REQUEST[ 'z' ] ) ? floatval( $_REQUEST[ 'z' ] ) : 0;
$top = isset( $_REQUEST[ 'top' ] ) ? floatval( $_REQUEST[ 'top' ] ) : 0;
$left = isset( $_REQUEST[ 'left' ] ) ? floatval( $_REQUEST[ 'left' ] ) : 0;
$width = isset( $_REQUEST[ 'width' ] ) ? floatval( $_REQUEST[ 'width' ] ) : 0;
$height = isset( $_REQUEST[ 'height' ] ) ? floatval( $_REQUEST[ 'height' ] ) : 0;
$zres = isset( $_REQUEST[ 'zres' ] ) ? floatval( $_REQUEST[ 'zres' ] ) : 0;

// the scale factor to volume bound the query in z-direction based on the z-resolution
$zbound = 1.0;
// limit number of retrieved treenodes
$limit = 400;

if ( $pid )
{
  if ( $uid )
  {
    
    // need relation: model_of, presynaptic_to, postsynaptic_to
    // need class: synapse, presynaptic terminal, postsynaptic terminal
    // retrieve class ids

    $areas = $db->getResult(
      'SELECT polygons.id AS "id",
           polygons.z AS z,
           polygons.polygon AS polygon,
           polygons.user_id AS user_id,       
           (polygons.z - '.$z.') AS z_diff           
       FROM polygons 
       WHERE polygons.project_id = '.$pid.'
        AND ( (polygons.lbound).x >= '.$left.' OR (polygons.ubound).x >= '.$left.' )
        AND ( (polygons.lbound).x <= '.( $left + $width ).' OR (polygons.ubound).x <= '.( $left + $width ).' )
        AND ( (polygons.lbound).y >= '.$top.' OR (polygons.ubound).y >= '.$top.' )
        AND ( (polygons.lbound).y <= '.( $top + $height ).' OR (polygons.ubound).y <= '.( $top + $height ).' )
        AND (polygons.lbound).z >= '.$z.' - '.$zbound.' * '.$zres.'
        AND (polygons.lbound).z <= '.$z.' + '.$zbound.' * '.$zres.'
        ORDER BY id, z_diff
        LIMIT '.$limit
    );

   
    // loop over and add type, parse polygon into numerical values
    {
    while ( list( $key, $val) = each( $areas ) )
    {
      $areas[$key]['type'] = "area";
      $polystr = $areas[$key]['polygon'];      
      $tok = strtok($polystr, '(), \t');      
      
      while ($tok !== false) {
        $xarr[] = floatval($tok);
        $tok = strtok('(), \t');
        $yarr[] = floatval($tok);
        $tok = strtok('(), \t');
      }
      $areas[$key]['x'] = $xarr;
      $areas[$key]['y'] = $yarr;
      unset($xarr);
      unset($yarr); 
     } 
    }
    
    echo makeJSON( $areas );

  }
  else
    echo makeJSON( array( 'error' => 'You are not logged in currently.  Please log in to be able to list treenodes.' ) );
}
else
  echo makeJSON( array( 'error' => 'Project closed. Can not apply operation.' ) );
  
?>
