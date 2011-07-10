<?php

include_once( 'errors.inc.php' );
include_once( 'db.pg.class.php' );
include_once( 'session.class.php' );
include_once( 'tools.inc.php' );
include_once( 'json.inc.php' );

$db =& getDB();
$ses =& getSession();

$uid = $ses->isSessionValid() ? $ses->getId() : 0;
if ( ! $uid ) {
    echo makeJSON( array( 'error' => 'You are not logged in currently.  Please log in to be able to update treenodes.' ) );
    return;
}

$areas = array();

foreach( $_REQUEST as $key => $value ) {
    preg_match('/^(\w+)([0-9]+)$/', $key, $matches);
    $real_key = $matches[1];
    $index = $matches[2];
    
    if( ! array_key_exists($index,$areas) ) {
        $areas[$index] = array();
    }
    $areas[$index][$real_key] = $value;
}

$required_keys = array( 'pid', 'area_id', 'z', 'polygon', 'lbound', 'ubound' );

$areas_updated = 0;

foreach( $areas as $area ) {
    foreach( $required_keys as $required_key ) {
        if( ! array_key_exists($required_key,$area) ) {
            echo makeJSON( array( 'error' => "Missing key: '$required_key' in index '$index'" ) );
            return;
        }
    }
    $pid = intval( $area['pid'] );
    if( ! $pid ) {
        /* FIXME: also check that this a project the user
           has access to.  This needs to be done *everywhere* ... */
        echo makeJSON( array( 'error' => 'Invalid project' ) );
        return;
    }
    $area_id = intval( $area['area_id'] );
    $z = floatval( $area['z'] );
    $polygon = $area['polygon'];
    $lbound = $area['lbound'];
    $ubound = $area['ubound'];
    
    $db->update("polygons", array('z' => $z, 'polygon' => $polygon, 'lbound' => $lbound, 
        'ubound' => $ubound), 'polygons.id = '.$area_id);   

    ++ $areas_updated;
}

echo makeJSON( array( 'updated' => $areas_updated ) );
return;

?>
