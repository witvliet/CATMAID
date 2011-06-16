<?php

include_once( 'errors.inc.php' );
include_once( 'db.pg.class.php' );
include_once( 'session.class.php' );
include_once( 'tools.inc.php' );
include_once( 'json.inc.php' );
// include_once( 'project.list.php' );  << need this to work
/*
todo: figure out how to catch errors from $db->insertIntoId commands 
   and use those to replace redundant $db->getResult commands
   for $user_id and $project_id, ie. $users and $projects
*/

$db =& getDB();

$username = isset( $_POST[ 'username' ] ) ? $_POST[ 'username' ] : '';
$realname = isset( $_POST[ 'realname' ] ) ? $_POST[ 'realname' ] : '';
$email = isset( $_POST[ 'email' ] ) ? $_POST[ 'email' ] : '';
$password = isset( $_POST[ 'password' ] ) ? $_POST[ 'password' ] : '';
$password2 = isset( $_POST[ 'password2' ] ) ? $_POST[ 'password2' ] : '';

if ($username && $realname && $email && $password && $password2) 
{
	if ($_POST['password'] !== $_POST['password2']) 
	{
		echo '{ error : "The passwords did not match." }';
	} 
	else if (strlen($_POST['password']) < 5) 
	{
		echo '{ error : "The password must be at least 5 characters long." }';
	} 
	else 
	{
		//$user_id =$db->insertIntoId('user',array('name' => $_POST['username'], 'pwd' => md5($_POST['password']), 'longname' => $_POST['realname']));
		//if ($user_id) 
		$users = $db->getResult(
			'SELECT	"name" AS "name"
				FROM "user"'
		);
		function format_names(&$name_element, $key) 
		{
			$name_element = $name_element['name'];
		}
		array_walk($users, 'format_names');
		if (in_array($username, $users))
		{
			echo '{ error : "That username is already taken."}';		
		}
		else
		{
			$user_id =$db->insertIntoId('user',array('name' => $_POST['username'], 'pwd' => md5($_POST['password']), 'longname' => $_POST['realname']));
			$projects = $db->getResult(   
				'SELECT	"project"."id" AS "pid"
					FROM "project"'
			);
			foreach ($projects as $p) 
			{
				$cpid = $p['pid'];
				$project_user_id = $db->insertIntoId('project_user', array('user_id' => $user_id, 'project_id' => $cpid));
				if (!$project_user_id) 
				{
					echo '{ error : "Linking your account with project $cpid failed." }';
				}
			}
			echo '{ notice : "Your account was created successfully - you can now log in."}';
			// echo dirname($_SERVER['PHP_SELF']);	

		}
	}
} 
else if (isset($_POST['username']) ||
           isset($_POST['realname']) ||
           isset($_POST['password']) ||
           isset($_POST['password2'])) 
{
	
        echo '{ error : "One of the required values was missing." }';
}
?>
