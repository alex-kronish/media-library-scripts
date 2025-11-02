#!/tools/conda/envs/Plex/bin/python

import time
import datetime
import requests
import json
import subprocess
import os
import shutil
import re
from operator import getitem
import eyed3
import logging


def current_timestamp():
    return datetime.datetime.now().strftime('%Y-%m-%d, %H:%M:%S')


def get_configuration():
    cwd=os.path.dirname(os.path.realpath(__file__))
    cfname=os.path.join(cwd,'radarr-sonarr.config.secret.json')
    cf=open(cfname,'rt+')
    conf=json.load(cf)
    cf.close()
    return conf


def telegram_notify(conf, msg, logger):
    tg_chat_id = conf['telegram_user_id']
    tg_api_key= conf['telegram_bot_api_key']
    logger.warning("Sending Telegram Message to "+str(tg_chat_id))
    payload_body={"chat_id":tg_chat_id,
                  "text": current_timestamp() + "\n\n"+  msg}
    url='https://api.telegram.org/bot'+tg_api_key+'/sendMessage'
    logger.warning("POST | "+url)
    logger.warning("BODY | "+json.dumps(payload_body))
    logger.warning("")
    p=requests.post(url,json=payload_body)
    logger.warning("RESPONSE CODE | "+str(p.status_code))
    logger.warning("RESPONSE BODY | "+json.dumps(p.json()))


def unmonitor_album(lidarr_album_ids, conf, logger):
    put_body={"albumIds":lidarr_album_ids.split(','), "monitored":False}
    url=conf['lidarr_host']+'/api/v1/album/monitor'
    api_key=conf['lidarr_api_key']
    api_headers={'X-Api-Key': api_key, 'Content-Type': 'application/json'}
    logger.info("PUT | "+url)
    logger.info("BODY | "+json.dumps(put_body))
    req=requests.put(url, headers=api_headers, json=put_body)
    http_status_code_2=req.status_code
    logger.info("HTTP Status Code = "+ str(http_status_code_2)+'\n')
    if http_status_code_2 < 200 or http_status_code_2 > 299:
        logger.error("Something went wrong calling the API to unmonitor the album")
        logger.error(req.text)
        msg='Error unmonitoring Album ID(s) '+json.dumps(lidarr_album_ids)+'\n\n'+os.environ.get(str(os.environ.get('lidarr_artist_name'))) + ' - '+os.environ.get(str(os.environ.get('lidarr_album_title')))
        telegram_notify(conf, msg, logger)
        return False
    else:
        logger.info("Successfully unmonitored...")
        return True


def cleanse_filesystem_unsafe_chars(input_string):
    unsafe_char_replacements = [
        {"unsafe": "?", "safe": ''},
        {"unsafe": "'", "safe": ''},
        {"unsafe": ":", "safe": '-'},
        {"unsafe": "\\", "safe": '+'},
        {"unsafe": "/", "safe": '+'},
        {"unsafe": "\"", "safe": ''},
        {"unsafe": "`", "safe": ''},
        {"unsafe": "’", "safe": ''},
        {"unsafe": "*", "safe": '_'}
    ]
    output_string = input_string
    for u in unsafe_char_replacements:
        output_string = output_string.replace(u["unsafe"], u["safe"])
    if re.search(r'\.+$',output_string):
        #print('matched ...')
        output_string=re.sub(r'\.+$','',output_string)
    return output_string


def normalize_dir(parent_dir, dir_name, logger):
    listing=os.listdir(parent_dir)
    listing_dict={}
    dir_name_lower=dir_name.lower()
    for l in listing:
        listing_dict[l.lower()]=l
    get_normalized=listing_dict.get(dir_name_lower)
    if get_normalized and get_normalized != dir_name:
        logger.info("Found a directory with a different case than the input:")
        logger.info("  Location: "+parent_dir)
        logger.info("  Input:    "+dir_name)
        logger.info("  Detected: "+get_normalized)
        logger.info("    Lowercase Search: "+dir_name_lower)
        return get_normalized
    else:
        return dir_name


def get_cover_art(mbid, target_dir, logger):
    url = 'https://coverartarchive.org/release/'+mbid
    logger.info('GET | '+url)
    req=requests.get(url)
    status=req.status_code
    logger.info("Response Code: "+str(status))
    selected={}
    if status==200:
        json_resp=req.json()
        selected=''
        for i in json_resp['images']:
            if i['front']==True:
                selected=i['image']
                logger.info("Image tagged as front cover in the response: "+selected)
        extn_regex=r'\.\w+$'
        cover_extension=re.search(extn_regex, selected).group(0)
        target_file=os.path.join(target_dir, 'folder'+cover_extension)
        logger.info('GET | '+selected)
        req_cover=requests.get(selected)
        req_status=req_cover.status_code
        logger.info(' Response Code: '+str(req_status))
        if req_status==200:
            cover_content=req_cover.content
            cov=open(target_file,'wb')
            cov.write(cover_content)
            cov.close()
            logger.info('Wrote file: '+target_file)
            return True
        else:
            logger.warning('Album Art process could not get the image file.')
            return False
    else:
        logger.warning( "Album Art process was not successful")
        return False


def ffmpeg_to_mp3(input_file, preprocess_backup_dir, logger, conf):
    output_file=re.sub(r'\.\w+$', '.mp3', input_file)
    cmd=['ffmpeg', '-i', input_file, '-ab', '320k', '-map_metadata', '0', '-id3v2_version', '3', output_file]
    logger.info(json.dumps(cmd))
    exit_code=subprocess_to_logfile(cmd, logger)
    logger.info('Exit Code: ' +str(exit_code))
    if exit_code==0:
        logger.info("Moving original file to preprocess dir")
        preproc_file=os.path.join(preprocess_backup_dir, os.path.basename(input_file))
        logger.info(input_file+" --> "+preproc_file)
        os.rename(input_file, preproc_file)
    else:
        logger.error("FFMPEG returned a non-zero exit code!")
        telegram_notify(conf, "FFMPEG Could not encode to mp3. Source File: "+input_file,logger)
        exit(99)
    logger.info("------------------------------------------------------------------------")
    return output_file


def apply_id3_rename(input_file_list, album_dir_normalized, logger, conf):
    eyed3.log.setLevel("ERROR")
    for f in input_file_list:
        mp3 = eyed3.load(f)
        time.sleep(.05)  #it throws errors if you read files too quickly?
        if mp3.tag.title is not None and mp3.tag.album is not None and mp3.tag.track_num[0] is not None and mp3.tag.artist is not None:
            new_fname = str(mp3.tag.artist) + ' - ' + str(mp3.tag.album) + ' - ' + str(mp3.tag.track_num[0]).zfill(2) + ' - ' + str(mp3.tag.title) + '.mp3'
            new_fname = cleanse_filesystem_unsafe_chars(new_fname)
            logger.info( f + ' --> ' + os.path.join(album_dir_normalized , new_fname))
            os.rename(f, os.path.join(album_dir_normalized , new_fname))
        else:
            logger.error( f + " has no ID3 tags! I'm stopping here so you can fix it.")
            telegram_notify(conf, "Source file did not have any ID3 tags! "+f,logger)
            exit(99)


def subprocess_to_logfile(subproc_command, logger):
    logger.info(" *****  SUBPROCESS COMMAND:")
    logger.info(json.dumps(subproc_command))
    logger.info('---------------------------------------------------------------------')
    subproc=subprocess.Popen(subproc_command, shell=False, stdout=subprocess.PIPE, 
                             stderr=subprocess.STDOUT, bufsize=1, universal_newlines=True)
    while (exit_code:=subproc.poll()) is None:
        if subproc.stdout:
            ffmpeg_line=subproc.stdout.readline()#.decode('utf-8')
            logger.info(str(ffmpeg_line).strip())
        if subproc.stderr:
            ffmpeg_line_stderr=subproc.stderr.readline()#.decode('utf-8')
            logger.info(str(ffmpeg_line_stderr).strip())
    proc_exit_code=subproc.returncode
    logger.info(' ***** Exit Code: ' +str(proc_exit_code))
    time.sleep(1)
    return proc_exit_code



if __name__=='__main__':
    process_dttm=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    conf=get_configuration()
    time.sleep(2)
    env_vars=dict(os.environ)
    env_vars_json=json.dumps(env_vars,indent=1)
    is_this_a_test=env_vars.get('lidarr_eventtype')
    album_name=str(os.environ.get('lidarr_album_title'))
    artist_name=str(os.environ.get('lidarr_artist_name'))
    logdir='/data/logs/'
    log_name='lidarr_'+cleanse_filesystem_unsafe_chars(artist_name) +'_'+cleanse_filesystem_unsafe_chars(album_name)+'_'+process_dttm+'.txt'
    log_filename=os.path.join(logdir, log_name)
    logging.basicConfig(filename=log_filename, level=logging.DEBUG, format='%(asctime)s | %(levelname)-8s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S' )
    logger=logging.getLogger(__name__)
    logger.info('--------- PROCESS START | '+current_timestamp() +' ---------')
    logger.info('Environment variables: ')
    for env_line in env_vars_json.splitlines():
        logger.info(env_line)
    logger.info('')
    if is_this_a_test=='Test':
        exit(0)
    preprocess_backup_dir=conf['preprocess_backup_dir']
    album_ids=os.environ.get('lidarr_album_id')
    album_musicbrainz_id=os.environ.get('lidarr_albumrelease_mbid')
    lidarr_download_dir=os.environ.get('lidarr_artist_path')
    individual_files_delimited=os.environ.get('lidarr_addedtrackpaths')
    individual_files=individual_files_delimited.split('|')
    album_name_cleaned=cleanse_filesystem_unsafe_chars(album_name)
    artist_name_cleaned=cleanse_filesystem_unsafe_chars(artist_name)
    logger.info("")
    logger.info("------------------------Setup and Existing Folder Check-------------------------------------")
    artist_dir_normalized=normalize_dir(conf['music_dir'], artist_name_cleaned,logger)
    full_artist_dir=os.path.join(conf['music_dir'],artist_dir_normalized)
    logger.info('Normalized Artist Directory: '+full_artist_dir)
    os.makedirs(full_artist_dir, exist_ok=True)
    album_dir_normalized=normalize_dir(full_artist_dir, album_name_cleaned,logger)
    full_album_dir=os.path.join(full_artist_dir, album_dir_normalized)
    logger.info('Normalized Album Directory: '+full_album_dir)
    os.makedirs(full_album_dir, exist_ok=True)
    mp3_files=[]
    for f in individual_files:
        logger.info("File Detected: "+ f)
        if f.lower().endswith('.flac') or f.lower().endswith('.m4a'):
            filebasename=os.path.basename(f)
            logger.info(f"------------------------File Conversion : {filebasename}-------------------------------------")
            new_mp3 = ffmpeg_to_mp3(f, preprocess_backup_dir, logger, conf)
            if new_mp3 is False:
                logger.error('Couldn\'t encode '+f)
            else:
                mp3_files.append(new_mp3)
        elif f.lower().endswith('.mp3'):
            mp3_files.append(f)
            logger.info(f"Appended to mp3 file list: {f}")
    logger.info("")
    logger.info("------------------------File Rename and Move-------------------------------------")
    apply_id3_rename(mp3_files, full_album_dir, logger, conf)
    logger.info("")
    logger.info("------------------------Cover Art Search-------------------------------------")
    art=get_cover_art(album_musicbrainz_id, full_album_dir, logger)
    logger.info("")
    logger.info("------------------------Unmonitor Album-------------------------------------")
    unmon=unmonitor_album(album_ids, conf, logger)
    logger.info("")
    logger.info("------------------------Plex Scanner-------------------------------------")
    plexscan=subprocess_to_logfile(['/home/kronish/bin/plex_media_scanner_music'], logger)
    #p_exit_code=plexscan
    logger.info("")
    logger.info("------------------------Navidrome Scanner-------------------------------------")
    n_exit_code=subprocess_to_logfile(['/home/kronish/bin/navidrome_scanner'],logger)
    logger.info("")
    logger.info("DONE!!!!!")
