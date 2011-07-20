<?php

/**
 * tools.inc.php
 *
 * @author Stephan Saalfeld <saalfeld@mpi-cbg.de>
 * @copyright Copyright (c) 2007, Stephan Saalfeld
 * @version 0.1 TrakEM2
 *
 */

/**
 * create a tree view node
 */
function tv_node( $data )
{
	// print_r( $data );
	$sOutput = '';
	$sOutput .= '{';	
	if( array_key_exists('data', $data) )
	{
		$sOutput .= '"data":{';
		if( array_key_exists('title', $data['data']))
		{
		$sOutput .= '"title":"'.$data['data']['title'].'"';
		}
		
		if( array_key_exists('icon', $data['data']))
		{
			$sOutput .= ',"icon":"'.$data['data']['icon'].'"';
		}
		
		$sOutput .= '}';
	};
	
	if( array_key_exists('attr', $data))
	{
		$sOutput .= ',"attr":{';
    $i = 0;
		foreach($data['attr'] as $key => $aval)
		{
		  if($i!=0) { $sOutput .= ','; }
			$sOutput .= '"'.$key.'" : "'.$aval.'"';		
      $i++;
		}
		$sOutput .= '}';
	}		
	
	if( array_key_exists('state', $data))
	{
		$sOutput .= ',"state":"'.$data['state'].'"';
	}
	
	if( array_key_exists('children', $data) )
	{
		$sOutput .= '",children":[';
		// add the children here
		foreach ($data['children'] as $key => $value ) {
			$sOutput .= tv_node($value);	
		};
		$sOutput .= ']';
	}
	
	$sOutput .= '}';
	
	return $sOutput;
			
}

/**
 * create a float array from a trakem2-postgres double precision[]
 *
 * @return array
 */
function pgDoubleArrayToPhp( $doubleArray )
{
	$doubleArray = str_replace( '{', '', $doubleArray );
	$doubleArray = str_replace( '}', '', $doubleArray );
	$doubleArray = explode( ',', $doubleArray );

	foreach ($doubleArray as &$value)
		$value = floatval( $value );

	return $doubleArray;
}

/**
 * create a x,y,z assoziative integer array from a trakem2-postgres integer3d(x,y,z)
 * 
 * @return array
 */
function pgIntegerArrayToPhp( $integerArray )
{
	$integerArray = str_replace( '{', '', $integerArray );
	$integerArray = str_replace( '}', '', $integerArray );
	$integerArray = explode( ',', $integerArray );

	foreach ($integerArray as &$value)
		$value = intval( $value );

	return $integerArray;
}

/** 
 * Get all files of a given directory .
 * 
 * @return array 
 */
function getFileList( $path )
{
    $dir = opendir( $path );
    $entry = readdir( $dir);
    $list = array();
    while ( $entry != '' )
    {
        if ( $entry != '.' && $entry != '..' )
            if ( is_file( $path.'/'.$entry ) ) $list[] = $entry;
        $entry = readdir( $dir );
    }
    closedir( $dir );
    sort( $list );
    return $list;
}

