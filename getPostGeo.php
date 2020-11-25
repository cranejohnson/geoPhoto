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

$final_box = "trash";

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

$filesToProcess = [];


/* if any emails found, iterate through each email */
if($emails) {

    $count = 1;

    /* put the newest emails on top */
    rsort($emails);

    /* for every email... */
    foreach($emails as $email_number)
    {

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

                /* prefix the email number to the filename in case two emails
                 * have the attachment with the same file name.
                 */
                $fp = fopen($dir."/kmz/".$email_number . "-" . $filename, "w+");
                fwrite($fp, $attachment['attachment']);
                fclose($fp);
                $filesToProcess[] = $dir."/kmz/".$email_number . "-" . $filename;
            }

        }
        imap_mail_move($mbox,$email_number,$final_box);
        if($count++ >= $max_emails) break;

    }

}

/* close the connection */
imap_close($inbox);

echo "Done with email processing";

foreach($filesToProcess as $file){
  $zip = new ZipArchive;
  $res = $zip->open($file);
  if ($res === TRUE) {
    $zip->extractTo('kml');
    $zip->close();
    echo 'woot!';
  } else {
    echo 'doh!';
  }
}

?>

