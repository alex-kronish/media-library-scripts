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


def get_configuration():
    cwd=os.path.dirname(os.path.realpath(__file__))
    cfname=os.path.join(cwd,'radarr-sonarr.config.secret.json')
    cf=open(cfname,'rt+')
    conf=json.load(cf)
    cf.close()
    return conf

def write_log(logfile, message):
    f=open(logfile,'at')
    f.write(message+'\n')
    f.close()

def stdout_stderr_tuple_to_string(input_tuple):
    z=[]
    for x in input_tuple:
        if x is not None:
            z.append(x.decode('utf-8'))
    y=''.join(z)
    return y

def telegram_notify(tg_chat_id, tg_api_key, msg,f2):
    payload_body={"chat_id":tg_chat_id,
                  "text": datetime.datetime.now().strftime('%Y-%m-%d  %H:%M:%S') + "\n\n"+  msg}
    url='https://api.telegram.org/bot'+tg_api_key+'/sendMessage'
    p=requests.post(url,json=payload_body)
    f2.write(json.dumps(p.json(),indent=1))

def unmonitor_album(lidarr_album_ids, conf, log):
    put_body={"albumIds":lidarr_album_ids.split(','), "monitored":False}
    url=conf['lidarr_host']+'/api/v1/album/monitor'
    api_key=conf['lidarr_api_key']
    api_headers={'X-Api-Key': api_key, 'Content-Type': 'application/json'}
    req=requests.put(url, headers=api_headers, json=put_body)
    http_status_code_2=req.status_code
    write_log(log, "HTTP Status Code = "+ str(http_status_code_2)+'\n')
    if http_status_code_2 < 200 or http_status_code_2 > 299:
        write_log(log,"Something went wrong calling the API to unmonitor the album")
        write_log(log,req.text+'\n')
        return False
    else:
        write_log(log,"Successfully unmonitored...")
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

def get_cover_art(mbid, target_dir, logfile_name):
    url = 'https://coverartarchive.org/release/'+mbid
    write_log(logfile_name, 'GET | '+url)
    req=requests.get(url)
    status=req.status_code
    write_log(logfile_name, "Response Code: "+str(status))
    
    selected={}
    if status==200:
        json_resp=req.json()
        selected=''
        for i in json_resp['images']:
            if i['front']==True:
                selected=i['image']
                write_log(logfile_name,"Image tagged as front cover in the response: "+selected)
        extn_regex=r'\.\w+$'
        cover_extension=re.search(extn_regex, selected).group(0)
        target_file=os.path.join(target_dir, 'folder'+cover_extension)
        write_log(logfile_name,'GET | '+selected)
        req_cover=requests.get(selected)
        req_status=req_cover.status_code
        write_log(logfile_name,' Response Code: '+str(req_status))
        if req_status==200:
            cover_content=req_cover.content
            cov=open(target_file,'wb')
            cov.write(cover_content)
            cov.close()
            write_log(logfile_name,'Wrote file: '+target_file)
            return True
        else:
            write_log(logfile_name,'Album Art process could not get the image file.')
            return False
    else:
        write_log(logfile_name, "Album Art process was not successful")
        return False



if __name__=='__main__':
    process_dttm=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    conf=get_configuration()
    time.sleep(2)
    env_vars=dict(os.environ)
    env_vars_json=json.dumps(env_vars,indent=1)
    album_name=os.environ.get('lidarr_artist_name')
    artist_name=os.environ.get('lidarr_album_title')
    logdir='/data/logs/'
    log_name='lidarr_'+cleanse_filesystem_unsafe_chars(artist_name) +'_'+cleanse_filesystem_unsafe_chars(album_name)+'_'+process_dttm+'.txt'
    logfile_name=os.path.join(logdir,log_name)
    write_log(logfile_name, '--------- PROCESS START | '+datetime.datetime.now().strftime('%Y-%m-%d  %H:%M:%S') +' ---------'+'\n')
    write_log(logfile_name, 'Environment variables: ')
    write_log(logfile_name, env_vars_json)
    write_log(logfile_name, '')
    album_ids=os.environ.get('lidarr_album_id')
    album_musicbrainz_id=os.environ.get('lidarr_albumrelease_mbid')
    lidarr_download_dir=os.environ.get('lidarr_artist_path')
    individual_files_delimited=os.environ.get('lidarr_addedtrackpaths')
    individual_files=individual_files_delimited.split('|')
    for f in individual_files:
        write_log(logfile_name,"File Detected: "+ f)
    art=get_cover_art(album_musicbrainz_id, lidarr_download_dir, logfile_name)
    unmon=unmonitor_album(album_ids, conf, logfile_name)
    sproc=subprocess.Popen(['/home/kronish/bin/mp3'],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    sproc_c=sproc.communicate()
    stdout,stderr=sproc_c
    for line in stdout.decode('utf-8').splitlines():
        write_log(logfile_name, line)