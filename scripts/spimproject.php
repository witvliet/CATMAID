<?php

include_once( 'errors.inc.php' );
include_once( 'db.pg.class.php' );

$db =& getDB();


// Start transaction
if (! $db->begin() ) {
	print_r ( array( 'error' => 'Could not start transaction.' ) );
	return;
}

try {
	$project_title = 'HisYFP sequence';
	$stack_title   = 'angle0 HisYFP sequence';
	$stack_base    = 'http://localhost/HisYFPseq/';

	$project_id = $db->insertIntoId('project',
		array(
			'title' => $project_title,
			'public' => true
		) );

	if (false === $project_id) {
		emitErrorAndExit($db, 'Failed to insert new project');
	}

	print( "created project " . $project_id . "\n" );



	$stack_id = $db->insertIntoId('stack',
		array(
			'title' => $stack_title,
			'dimension' => '{1388, 1040, 81, 16}',
			'resolution' => '{1, 1, 1, 1}',
			'image_base' => $stack_base,
			'comment' => '<p>&copy;2011 Tobias Pietzsch</p>',
			'trakem2_project' => false
		) );

	if (false === $stack_id) {
		emitErrorAndExit($db, 'Failed to insert new stack');
	}

	print( "created stack " . $stack_id . "\n" );



	$q = $db->insertInto('project_stack',
		array(
			'project_id' => $project_id,
			'stack_id' => $stack_id,
			'translation' => '{0, 0, 0, 0}'
		) );

	if (false === $q) {
		emitErrorAndExit($db, 'Failed to create project_stack association');
	}



	foreach( array(1,2,3) as $user_id )
	{
		$q = $db->insertInto('project_user',
			array(
				'project_id' => $project_id,
				'user_id' => $user_id
			) );

		if (false === $q) {
			emitErrorAndExit($db, 'Failed to create user_stack association');
		}
	}



	if (! $db->commit() ) {
		emitErrorAndExit( $db, 'Failed to commit!' );
	}
} catch (Exception $e) {
	print_r ($db);
	print_r ('ERROR: ');
	print_r ($e);
}

?>
