<?php
/**
 * Description: This script gets messages from the specified mailbox and
 * drops the data into folder which then gets pushed over to AWIPS. 
 * Shef data will only be ingested 
 * into the local RFC shef encoder.
 *
 * This scripts requires php5 IMAP support. This was installed on redrock with
 * the following command:
 *       'zypper install php5-imap'
 *
 *

 *
 * @package get_igage
 * @author Crane Johnson <benjamin.johnson@noaa.gov>
 * @version 0.1
 */


chdir(dirname(__FILE__));
date_default_timezone_set('UTC');

/* Include config file for paths etc..... */
define("PROJECT_ROOT",dirname(__FILE__).'/../');
#Private file
define("CREDENTIALS_FILE","/usr/local/apps/scripts/bcj/hydroTools/login.php");
define("LOG_TYPE","FILE");
define("LOG_DIRECTORY",PROJECT_ROOT."log/");
define("TEMP_DIRECTORY",PROJECT_ROOT."data/");
define("TO_LDAD","/usr/local/apps/scripts/bcj/hydroTools/TO_LDAD/");
define("SHEF_HEADER","SRAK58 PACR ".date('dHi')."\nACRRR3ACR \nWGET DATA REPORT \n\n");


//Pear log package
require_once ('../../lib/Pear/Log.php');
//Pear cache_lite package
require_once('../../lib/Pear/Cache/Lite.php');

include_once(CREDENTIALS_FILE);

/* Include config file for paths etc..... */
$mysqli->select_db("aprfc");

date_default_timezone_set('UTC');

/**
 * Setup PEAR logging utility
 */

//Console gets more information, file and sql only get info and above errors
$consoleMask = Log::MAX(PEAR_LOG_DEBUG);
$fileMask = Log::MAX(PEAR_LOG_INFO);
$sqlMask = Log::MAX(PEAR_LOG_INFO);

$sessionId = 'ID:'.time();

if(LOG_TYPE == 'FILE'){
    $script = basename(__FILE__, '.php');
    $file = Log::factory('file',LOG_DIRECTORY.$script.'.log',$sessionId);
    $file->setMask($fileMask);
    $console = Log::factory('console','',$sessionId);
    $console->setMask($consoleMask);
    $logger = Log::singleton('composite');
    $logger->addChild($console);
    $logger->addChild($file);
}
if(LOG_TYPE == 'NULL'){
    $logger = Log::singleton('null');
}


/**
 *
 *  MAIN PROGRAM LOGIC
 */

$logger->log("END",PEAR_LOG_INFO);
$sendshef = 0;


#################Mailbox Configuration Settings########################
$username = GMAIL_USERNAME;
$password = GMAIL_PASSWORD;

#//Which folders or label do you want to access? - Example: INBOX, All Mail, Trash, labelname
#//Note: It is case sensitive
$imapmainbox = "daveSnow";
$messagestatus = "ALL";


//Gmail Connection String
$imapaddress = "{imap.gmail.com:993/imap/ssl}";

//Gmail host with folder
$hostname = $imapaddress . $imapmainbox;

$final_box = "trash";

$verbose = false;

$mbox = imap_open($hostname, $username,$password);

if(!$mbox){
    $logger->log("Could not open sheffile inbox ($imapmainbox in account $username) aborting....",PEAR_LOG_ERR);
        exit();
}

#####Spit out the Total Number of Messages from Iridium

$check = imap_check($mbox);

$sbdmes = $check->Nmsgs;

$logger->log("$sbdmes total messages in sheffile inbox",PEAR_LOG_INFO);

$numnew =  imap_num_recent($mbox);


$data = SHEF_HEADER;
$numData = 0;

######Process each message
$emails = imap_search($mbox,'ALL');
if($emails){
    arsort($emails); //JUST DO ARSORT
    foreach($emails as $email_number) {
        $sitedata = array();
        $msgno = $email_number;
        $text = "";
        ######Get the message header information
        $header = imap_header($mbox,$msgno);
        $date = strtotime($header->date);
        ######Get the file name and parse out the datestamp
        $string = imap_body($mbox,$msgno);
        $lines = preg_split('/$\R?^/m', $string);
        $snowDepth = 0;
        $id = '';
        foreach($lines as $line){ 
            if(strpos($line,':') == false ) continue;
            $parts = explode(':',$line);
            if( strpos($parts[0],'NWSLI') !== false ) $id = trim($parts[1]);
            if( strpos($parts[0],'SD') !== false ) {
                $numData = $numData + 1;
                $snowDepth = trim($parts[1]);
                # Example shef: AR SIXA2 180306 Z DH0515/DC1803072333/HGIRZ -9999
                $dc = date('\D\CymdHi');
                $shefData = ".AR ".$id." ".date('ymd \Z \D\HHi',$date)."/$dc/SDIRZ $snowDepth\n";
                $shefData = trim($shefData);
                $logger->log("shef data:$shefData",PEAR_LOG_INFO);
                if(substr($shefData, 0, 3 ) === ".AR")  $data .= $shefData."\n";
            }   
        }
        imap_delete($mbox, $msgno);
        imap_expunge($mbox);
    }
}  #Outer if loop


if($numData> 0){
    $filename = 'sheffile.'.date('ymdHi');
    file_put_contents(TEMP_DIRECTORY.$filename, $data);
    if(file_put_contents(TO_LDAD.$filename, $data)){
        $logger->log("Moved shef data to LDAD",PEAR_LOG_INFO);
    }    
}  #If data loop

$logger->log("END",PEAR_LOG_INFO);


?>

