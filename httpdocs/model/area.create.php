<?php

include_once( 'errors.inc.php' );
include_once( 'db.pg.class.php' );
include_once( 'session.class.php' );
include_once( 'tools.inc.php' );
include_once( 'json.inc.php' );
include_once( 'utils.php' );

$db =& getDB();
$ses =& getSession();

$pid = isset( $_REQUEST[ 'pid' ] ) ? intval( $_REQUEST[ 'pid' ] ) : 0;
$uid = $ses->isSessionValid() ? $ses->getId() : 0;

# Check preconditions:

# 1. There must be a project id
if ( ! $pid ) {
  echo json_encode( array( 'error' => 'Project closed. Cannot apply operation.' ) );
	return;
}

# 2. There must be a user id
if ( ! $uid ) {
    echo json_encode( array( 'error' => 'You are not logged in currently.  Please log in to be able to add treenodes.' ) );
	return;
}

# 3. The user must have permissions to edit this tree
# TODO -- currently all users can edit everything



// Add a new treenode to the database
// ----------------------------------

// 1. Add new area
// TODO: The area should be associated with either an area list or a treenode.
// return: new area id


// The X,Y,Z coordinate of the treenode to be created, and its properties:
$x = isset( $_REQUEST[ 'x' ] ) ? floatval( $_REQUEST[ 'x' ] ) : 0;
$y = isset( $_REQUEST[ 'y' ] ) ? floatval( $_REQUEST[ 'y' ] ) : 0;
$z = isset( $_REQUEST[ 'z' ] ) ? floatval( $_REQUEST[ 'z' ] ) : 0;



# Get IDs for the classes and relations in this project

/*
$skid = $db->getClassId( $pid, "skeleton" );
if (!$skid) {
	echo json_encode( array( 'error' => 'Can not find "skeleton" class for this project' ) );
	return;
}

$nid = $db->getClassId( $pid, "neuron" );
if (!$nid) {
	echo json_encode( array( 'error' => 'Can not find "neuron" class for this project' ) );
	return;
}

$eleof = $db->getRelationId( $pid, "element_of" );
if (!$eleof) {
	echo json_encode( array( 'error' => 'Can not find "element_of" relation for this project' ) );
	return;
}

$modid = $db->getRelationId( $pid, "model_of" );
if (!$modid) {
	echo json_encode( array( 'error' => 'Can not find "model_of" relation for this project' ) );
	return;
}

$partof_id = $db->getRelationId( $pid, "part_of" );
if (!$partof_id) {
	echo json_encode( array( 'error' => 'Can not find "part_of" relation for this project' ) );
	return;
}
*/


// Start transaction
if (! $db->begin() ) {
	echo json_encode( array( 'error' => 'Could not start transaction.' ) );
	return;
}

try {
    
	// The result JSON message, if any:
	$json = false;

  $data = array(
    'user_id' => $uid,
		'project_id' => $pid,
    'z' => $z,
		'polygon' => '(('.$x.','.$y.'))',
    'lbound' => '('.$x.','.$y.','.$z.')',
    'ubound' => '('.$x.','.$y.','.$z.')'
    );
		
	$polyid = $db->insertIntoId('polygons', $data );

	if (false === $polyid) {
		emitErrorAndExit($db, 'Error while trying to insert treenode.');
	}

	// RESULT:
	$json = array( 'polygonid' => $polyid);

	
	if ($json) {
		if (! $db->commit() ) {
			emitErrorAndExit( $db, 'Failed to commit for expand!' );
		}
		echo json_encode( $json );
	} else {
		emitErrorAndExit( $db, 'Failed to produce a JSON string!' );
	}

} catch (Exception $e) {
	emitErrorAndExit( $db, 'ERROR: '.$e );
}

?>
