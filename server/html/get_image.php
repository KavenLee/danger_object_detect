<?php

date_default_timezone_set('Asia/Seoul');
@header("Content-Type: application/json;charset=utf-8");

$fname= $_GET['id'];

$dir= $_SERVER["DOCUMENT_ROOT"];
$dir=$dir.DIRECTORY_SEPARATOR.'file';

if(file_exists($dir.DIRECTORY_SEPARATOR.$fname.'.json')){
        $json_file=file_get_contents($dir.DIRECTORY_SEPARATOR.$fname.'.json');
        echo $json_file;
}else{
        $failed_json=new stdClass();
		#$now=DateTime::createFromFormat('U.u', microtime(true));
        #$failed_json->Time=$now->format('Y-m-d H:i:s.u');
		$now = new DateTime();
        $failed_json->Time=$now->format("Y-m-d H:i:s.v"); # v = millisec
        $failed_json->ErrorCode=1;
        $failed_json->Detected=false;
        $failed_json->Base64Image="";

        $result=json_encode($failed_json);
        echo $result;
}

?>