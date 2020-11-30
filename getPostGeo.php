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
 * @author Crane Johnson <benjamin.johnson@noaa.gov>
 * @version 0.1
 */


chdir(dirname(__FILE__));
date_default_timezone_set('UTC');

require_once "/var/www/html/tools/PHPMailer/PHPMailerAutoload.php";

/* Include config file for paths etc..... */
#Private file
define("CREDENTIALS_FILE","/usr/local/apps/scripts/bcj/hydroTools/login.php");

include_once(CREDENTIALS_FILE);

$dir = dirname(__FILE__);

/**
 *
 *  MAIN PROGRAM LOGIC
 */


#################Mailbox Configuration Settings########################
$username = GMAIL_USERNAME;
$password = GMAIL_PASSWORD;

#//Which folders or label do you want to access? - Example: INBOX, All Mail, Trash, labelname
#//Note: It is case sensitive
$imapmainbox = "geoPhoto";
$messagestatus = "ALL";


//Gmail Connection String
$imapaddress = "{imap.gmail.com:993/imap/ssl}";

//Gmail host with folder
$hostname = $imapaddress . $imapmainbox;

echo "Clearing tmp directory.....\n";
$numRemoved = 0;
$tempDir = "tmp/";
$di = new RecursiveDirectoryIterator($tempDir, FilesystemIterator::SKIP_DOTS);
$ri = new RecursiveIteratorIterator($di, RecursiveIteratorIterator::CHILD_FIRST);
foreach ( $ri as $file ) {
    $file->isDir() ?  rmdir($file) : unlink($file);
    $numRemoved++;
}

echo "$numRemoved files removed from tmp directory.\n";



/* try to connect */
$inbox = imap_open($hostname,$username,$password) or die('Cannot connect to Gmail: ' . imap_last_error());


/* get all new emails. If set to 'ALL' instead
 * of 'NEW' retrieves all the emails, but can be
 * resource intensive, so the following variable,
 * $max_emails, puts the limit on the number of emails downloaded.
 *
 */
$emails = imap_search($inbox,'ALL');

/* useful only if the above search is set to 'ALL' */
$max_emails = 16;

$filesToProcess = array();






/* if any emails found, iterate through each email */
if($emails) {

    $count = 1;

    /* put the newest emails on top */
    rsort($emails);

    /* for every email... */
    foreach($emails as $email_number)
    {
	echo "Processing email #:$email_number\n";
        $header = imap_headerinfo($inbox, $email_number); // get first mails header
	
	/* get information specific to this email */
        $overview = imap_fetch_overview($inbox,$email_number,0);

        /* get mail message */
        $message = imap_fetchbody($inbox,$email_number,2);

        /* get mail structure */
        $structure = imap_fetchstructure($inbox, $email_number);

        $attachments = array();

        /* if any attachments found... */
        if(isset($structure->parts) && count($structure->parts))
        {
            for($i = 0; $i < count($structure->parts); $i++)
            {
                $attachments[$i] = array(
                    'is_attachment' => false,
                    'filename' => '',
                    'name' => '',
                    'attachment' => ''
                );

                if($structure->parts[$i]->ifdparameters)
                {
                    foreach($structure->parts[$i]->dparameters as $object)
                    {
                        if(strtolower($object->attribute) == 'filename')
                        {
                            $attachments[$i]['is_attachment'] = true;
                            $attachments[$i]['filename'] = $object->value;
                        }
                    }
                }

                if($structure->parts[$i]->ifparameters)
                {
                    foreach($structure->parts[$i]->parameters as $object)
                    {
                        if(strtolower($object->attribute) == 'name')
                        {
                            $attachments[$i]['is_attachment'] = true;
                            $attachments[$i]['name'] = $object->value;
                        }
                    }
                }

                if($attachments[$i]['is_attachment'])
                {
                    $attachments[$i]['attachment'] = imap_fetchbody($inbox, $email_number, $i+1);

                    /* 4 = QUOTED-PRINTABLE encoding */
                    if($structure->parts[$i]->encoding == 3)
                    {
                        $attachments[$i]['attachment'] = base64_decode($attachments[$i]['attachment']);
                    }
                    /* 3 = BASE64 encoding */
                    elseif($structure->parts[$i]->encoding == 4)
                    {
                        $attachments[$i]['attachment'] = quoted_printable_decode($attachments[$i]['attachment']);
                    }
                }
            }
        }

        /* iterate through each attachment and save it */
        foreach($attachments as $attachment)
        {
            if($attachment['is_attachment'] == 1)
            {
                $filename = $attachment['name'];
                if(empty($filename)) $filename = $attachment['filename'];

                if(empty($filename)) $filename = time() . ".dat";

		$fp = fopen("toUpload/".$filename, "w+");
                $address =  $header->from[0]->mailbox."@".$header->from[0]->host."\n";		
		$filesToProcess[$filename]= $address;
		fwrite($fp, $attachment['attachment']);
                fclose($fp);
            }

        }
        imap_mail_move($inbox,$email_number,$final_box);
        imap_delete($inbox,$email_number);
        imap_expunge($inbox);
        if($count++ >= $max_emails) break;

    }

}

$mail = new PHPMailer;
$mail->FromName = 'nws.ar.aprfc';
$mail->addAddress('benjamin.johnson@noaa.gov','Crane');


/* close the connection */
imap_close($inbox);

$files = glob("toUpload/*.kmz");
foreach ($files as $f){
  $name = basename($f);	
  if(array_key_exists($name,$filesToProcess)){
    continue;
  }else{
    $filesToProcess[$name] = '';
  }

}


echo "Done with email processing\n\n\n";

if(count($filesToProcess) == 0){
  echo "No messages to process, exiting.\n";

  exit();
}


$emailMessage = "";
foreach($filesToProcess as $file=>$email){
  #Move kmz to NIDS for viewing
  $basename = $file;
  $filename = basename($file,".kmz");

  $emailMessage .= "Working on file: ".$basename."\n\n";
  $emailMessage .= "https://www.weather.gov/aprfc/geoPhoto?photoMeta=".$filename."\n\n";
  $emailMessage .= "Files:\n";

  copy("toUpload/".$file,'toRsync/cms_publicdata+geoPhoto+'.$basename);
  $emailMessage .= 'toRsync/cms_publicdata+geoPhoto+'.$basename."\n";
  $zip = new ZipArchive;
  echo $file."\n";
  $res = $zip->open("toUpload/".$file);
  if ($res === TRUE) {
    $zip->extractTo('tmp');
    $zip->close();
    $gDir = 'tmp/geoPhotos/';
    $files = preg_grep('/^([^.])/',scandir($gDir));
    $count = 0;
    foreach($files as $f){
      $count ++;
      if(strpos($f,".html") !== false) continue;
      if(strpos($f,".json") !== false){
        if($f){       
          copy($gDir.$f,'toRsync/cms_publicdata+geoPhoto+'.$f);
          $emailMessage .= 'toRsync/cms_publicdata+geoPhoto+'.$f."\n";
        }
      }else{
        if($f){
          copy($gDir.$f,'toRsync/cms_images+geoPhotos+'.$f);
          $emailMessage .= 'toRsync/cms_images+geoPhotos+'.$f."\n";
        }
      }
    }
    $emailMessage .= "\n\nFiles to be rsynced: ".$count."\n";
  } else {
    echo 'doh!';
  }
  
  rename("toUpload/".$file,"archive/".$basename);
 
  $mail = new PHPMailer;
  $mail->FromName = 'nws.ar.aprfc';
  $mail->addAddress('benjamin.johnson@noaa.gov','Crane');
  $mail->addAddress($email);
  $mail->Subject = "geoPhoto Upload for: ".$basename;
  $mail->Body = $emailMessage;
  if(!$mail->send()){
    echo $mail->ErrorInfo;
  }  

}

system('rsync -vzrt --remove-source-files toRsync/ 10.251.3.37::nids_incoming_aprfc');

?>

