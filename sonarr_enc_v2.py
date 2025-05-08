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


def name_override(name_overrides, input_name):
    new=name_overrides.get(input_name)
    if new is not None:
        return new
    else:
        return input_name


def stdout_stderr_tuple_to_string(input_tuple):
    z=[]
    for x in input_tuple:
        if x is not None:
            z.append(x.decode('utf-8'))
    y=''.join(z)
    return y


def opensubtitles_api_call(ost_user_id, ost_pw, ost_api_key, season_num, episode_num, show_imdb_id, plex_file_path, video_filename, logfile):
    logfile.write("--------------------------------------------------------------------------------------\n")
    logfile.write("-- Subtitles were not detected in the source file. Checking the opensubtitles.org API\n")
    api_key=ost_api_key
    auth_post_body={"username":ost_user_id,"password":ost_pw}
    search_url_params={'episode_number':episode_num,
                       'season_number':season_num,
                       'imdb_id':show_imdb_id,
                       'languages':'en'}
    search_url='https://api.opensubtitles.com/api/v1/subtitles'
    auth_url='https://api.opensubtitles.com/api/v1/login'
    loop=True
    attempts=0
    while loop:
        req=requests.get(search_url, headers={"Api-Key":api_key,"User-Agent":"PostmanRuntime/7.26.8","Accept":"*/*","Content-Type":"application/json"}, params=search_url_params)
        logfile.write("GET | " + req.url +'\n')
        if req.status_code!=200:
            logfile.write("HTTP call was not successful:\n")
            logfile.write(str(req.status_code)+'\n')
            logfile.write(req.text+'\n')
            time.sleep(30)  #try & dodge the intermittent cloudflare 502
            attempts=attempts+1
        else:
            loop=False
        if len(req.text)==0:
            logfile.write('The response from the search was empty. It\'s likely there are no subs files out there for this episode.'+'\n')
            loop=False
        if attempts==5:
            loop=False
            return None
            #after 5 attempts lets fucking get outta here.
    resp=req.json()
    #logfile.write(json.dumps(resp,indent=1))
    response_data=resp['data']
    if len(response_data)==0:
        logfile.write('The response from the search was empty. It\'s likely there are no subs files out there for this episode.'+'\n')
        return None
    response_data.sort(key=lambda x:getitem(x['attributes'],'download_count'), reverse=True)
    popularity_contest=response_data[0]
    logfile.write(json.dumps(popularity_contest,indent=1)+'\n')
    file_id=popularity_contest['attributes']['files'][0]['file_id']
    loop2=True
    attempts=0
    while loop2:
        attempts=attempts+1
        auth_req=requests.post(auth_url, headers={"Api-Key":api_key,"User-Agent":"PostmanRuntime/7.26.8","Accept":"*/*","Content-Type":"application/json"}, json=auth_post_body)
        if auth_req.status_code!=200:
            logfile.write("Open Subtitles API login did not work. Did you reset your password?"+'\n')
            logfile.write(str(auth_req.status_code)+'\n')
            logfile.write(req.text+'\n')
            logfile.write(req.headers+'\n')
            time.sleep(120) #try and dodge the too many requests 429 error
            if attempts==5:
                return None
        else:
            loop2=False
    auth_resp=auth_req.json()
    auth_token=auth_resp["token"]
    authorization='Bearer '+auth_token
    download_url='https://api.opensubtitles.com/api/v1/download'
    download_req_body={"file_id":file_id}
    download_req=requests.post(download_url, headers={"Api-Key":api_key,"User-Agent":"PostmanRuntime/7.26.8","Accept":"*/*","Content-Type":"application/json", 'Authorization':authorization}, json=download_req_body)
    if download_req.status_code != 200:
        logfile.write("Download request failed....."+'\n')
        logfile.write(str(download_req.status_code)+'\n')
        logfile.write(download_req.text+'\n')
        return False
    download_resp=download_req.json()
    logfile.write(json.dumps(download_resp,indent=1)+'\n')
    download_file_name=download_resp['file_name']
    download_link=download_resp['link']
    logfile.write(download_link+'\n')
    logfile.write(download_file_name+'\n')
    extn_regex=r'\.\w+$'
    subtitle_file_extension=re.search(extn_regex, download_file_name).group(0)
    subtitle_new_filename=os.path.join(plex_file_path,re.sub(extn_regex,subtitle_file_extension,video_filename))
    logfile.write("Subtitle file will be saved as: "+subtitle_new_filename+'\n')
    subs_req=requests.get(download_link, headers={"Api-Key":api_key,"User-Agent":"PostmanRuntime/7.26.8","Accept":"*/*","Content-Type":"application/json", 'Authorization':authorization})
    subsfile=open(subtitle_new_filename, 'wb+')
    subsfile.write(subs_req.content)
    subsfile.close()
    logfile.write("Subtitle process complete."+'\n')
    return True


def unmonitor_episode(episode_id,f2, sonarr_api_key, sonarr_host):
    api_key=sonarr_api_key
    host=sonarr_host
    api_headers={'X-Api-Key': api_key, 'Content-Type': 'application/json'}
    put_url=host+'/api/v3/episode/monitor'
    episode_data2={ "episodeIds": episode_id.split(','),
                    "monitored": False }
    f2.write("PUT | "+put_url+'\n')
    f2.write("PUT BODY: "+'\n')
    f2.write(json.dumps(episode_data2, indent=1)+'\n')
    episode_put=requests.put(put_url, headers=api_headers, json=episode_data2)
    http_status_code_2=episode_put.status_code
    f2.write("HTTP Status Code = "+ str(http_status_code_2)+'\n')
    if http_status_code_2 < 200 or http_status_code_2 > 299:
        f2.write("Something went wrong calling the API to unmonitor the episode"+'\n')
        f2.write(episode_put.text+'\n')
        return False
    else:
        f2.write("Successfully unmonitored..."+'\n')
        return True


def get_scantype(minfo):
    interlacing_strings=['Interleaved','Interlaced','MBAFF']
    interlaced_flag=False
    scan_type=None
    for x in minfo['media']['track']:
        if x['@type']=='Video' and (x.get('@typeorder') is None or x.get('@typeorder')==1):
            scan_type=x.get('ScanType')
    if scan_type is not None:
        if scan_type in interlacing_strings:
            interlaced_flag=True
    if interlaced_flag:
        return "Interlaced"
    else:
        return "Progressive"


def get_subtitle_mapping(minfo):
    subtitle_array=[]
    file_format='.mkv'
    subtitles_found=False
    for x in minfo['media']['track']:
        if x['@type']=='Text':
            if str(x.get('Language')).lower() =='en':
                subtitles_found=True #the subs need to be english otherwise we should still attempt to search opensubs
            subtitle_codec=x.get('CodecID')
            if subtitle_codec is not None and subtitle_codec in ['tx3g']:
                file_format='.mp4'
            if subtitle_codec is not None and subtitle_codec in ['S_VOBSUB','6','S_TEXT/UTF8','S_DVBSUB','S_HDMV/PGS','S_TEXT/ASS','tx3g']:
                track=x.get('@typeorder')
                if track is not None:
                    track_id=int(track)-1
                    trackmapping=['-map','0:s:'+ str(track_id)]
                    subtitle_array=subtitle_array+trackmapping
                else:
                    track_id=0
                    trackmapping=['-map','0:s:'+ str(track_id)]
                    subtitle_array=subtitle_array+trackmapping
    return subtitle_array, file_format, subtitles_found


def get_bitdepth(minfo):
    for x in minfo['media']['track']:
        if x['@type']=='Video' and (x.get('@typeorder')==0 or x.get('@typeorder') is None):
            return x.get('BitDepth')
    return "8"


def move_sonarr_to_plex(encoded_file, sonarr_base, plex_base, f2, name_overrides):
    f2.write("----------- Moving file to Plex:"+'\n'+'\n')
    source_file_list=encoded_file.split(os.path.sep)
    for i in sonarr_base.split(os.path.sep):
        source_file_list.remove(i)
    series_folder_name_orig = source_file_list[0].replace('\'','')
    series_folder_name=name_override(name_overrides,series_folder_name_orig).replace('／','-')
    season_folder_name = source_file_list[1].replace('\'','').replace('／','-')
    episode_file_name= source_file_list[2].replace('\'','').replace('／','-')
    f2.write("Original folder name: "+series_folder_name_orig + "\n Updated folder name: " + str(series_folder_name))
    if series_folder_name is None:
        series_folder_name=series_folder_name_orig
    else:
        episode_file_name=episode_file_name.replace(series_folder_name_orig, series_folder_name)
    #plex_base='/data/TV Shows'
    qualified_series_folder_name=os.path.join(plex_base,series_folder_name)
    qualified_season_folder_name=os.path.join(qualified_series_folder_name,season_folder_name)
    qualified_episode_filename=os.path.join(qualified_season_folder_name,episode_file_name)
    if os.path.exists(qualified_series_folder_name):
        f2.write("Series folder already exists - "+qualified_series_folder_name+'\n')
    else:
        f2.write("Series folder does not exist, creating it"+'\n')
        os.mkdir(qualified_series_folder_name)
    if os.path.exists(qualified_season_folder_name):
        f2.write("Season folder already exists - "+qualified_season_folder_name+'\n')
    else:
        f2.write("Season folder does not exist, creating it"+'\n')
        os.mkdir(qualified_season_folder_name)
    f2.write("TARGET FILE: "+ qualified_episode_filename+'\n')
    f2.write("SOURCE FILE: "+ encoded_file+'\n')
    shutil.move(encoded_file,qualified_episode_filename)
    touch(qualified_series_folder_name)
    touch(qualified_season_folder_name)
    touch(plex_base)
    return qualified_season_folder_name, qualified_episode_filename


def telegram_notify(tg_chat_id, tg_api_key, msg,f2):
    payload_body={"chat_id":tg_chat_id,
                  "text": datetime.datetime.now().strftime('%Y-%m-%d  %H:%M:%S') + "\n\n"+  msg}
    url='https://api.telegram.org/bot'+tg_api_key+'/sendMessage'
    p=requests.post(url,json=payload_body)
    f2.write(json.dumps(p.json(),indent=1))


def touch(input_file):
    subprocess.Popen('touch \''+input_file.replace('\'','\'\\\'\'')+'\'', shell=True)


def main():
    process_dttm=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    conf=get_configuration()
    time.sleep(2)
    sonarr_eventtype=os.environ.get('sonarr_eventtype')
    ffmpeg=conf['ffmpeg_binary']
    encode_dir=conf['ffmpeg_encode_dir']
    preproc_dir=conf['preprocess_backup_dir']
    ost_api_key=conf['opensubtitles_api_key']
    ost_user_id=conf['opensubtitles_user_id']
    ost_passwd=conf['opensubtitles_password']
    name_overrides=conf['name_overrides']
    sonarr_api_key=conf['sonarr_api_key']
    sonarr_host=conf['sonarr_host']
    log_dir=conf['log_dir']
    telegram_user_id=conf['telegram_user_id']
    telegram_bot_api_key=conf['telegram_bot_api_key']
    sonarr_dir=conf['sonarr_dir']
    plex_dir=conf['plex_tv_dir']
    extn_regex=r'\.\w+$'  #i know, lol
    disallowed_file_extensions=conf['disallowed_extensions'] #wow i bet they had to put on these warning labels one at a time
    use_new_override=False
    interlaced=False
    ten_bit=False
    subtitles_found=False
    if sonarr_eventtype is None or sonarr_eventtype=='Test':
        print("Running in test mode... Encoding but not moving files.")
        sonarr_episode_id=-1
        move_files=False
        sonarr_episodefile_path='/data/Unsorted/test_files/Joe Pera Talks with You - S01E01 - Joe Pera Shows You Iron.mkv'
        sonarr_series_id=-1
    else:
        sonarr_episodefile_path = os.environ.get('sonarr_episodefile_path')
        sonarr_episode_id = os.environ.get('sonarr_episodefile_episodeids')
        sonarr_series_id=os.environ.get('sonarr_series_id')
        move_files=True
        touch(sonarr_episodefile_path)
    sonarr_file_basename = os.path.basename(sonarr_episodefile_path)
    orig_file_extension=re.search(extn_regex, sonarr_file_basename).group(0)
    mediainfo_cmd="/usr/bin/mediainfo --output=JSON \'"+sonarr_episodefile_path.replace('\'','\'\\\'\'')+"\'"
    mediainfo_sbp=subprocess.Popen(mediainfo_cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
    mediainfo_output=stdout_stderr_tuple_to_string(mediainfo_sbp)
    mediainfo=json.loads(mediainfo_output)
    output_extension='.mkv'
    quality='28'  #cq:v value
    if sonarr_series_id in ['68','92']: # some shows i may wish to compress more
        quality='32'
    # ------------- Detect Needed Video Filters ----------------
    vfilter=[]
    if get_scantype(mediainfo)=='Interlaced':
        interlaced=True
        use_new_override=True
        vfilter.append('yadif')
    if get_bitdepth(mediainfo)=='10':
        ten_bit=True
        use_new_override=True
        vfilter.append('format=yuv420p')
    # -------------- Construct vfilter arg ----------------------
    if len(vfilter)>0:
        vf=['-vf',','.join(vfilter)]
    else:
        vf=[]
    # -------------- Exclude .ts and .avi files -----------------
    if orig_file_extension in disallowed_file_extensions:
        use_new_override=True
    subtitles_track_map, output_extension, subtitles_found=get_subtitle_mapping(mediainfo)
    # -------------- One two three let's ENCODE!!!!! ------------
    output_file_name=re.sub(extn_regex,output_extension,sonarr_file_basename)
    if len(output_file_name)>=100:
        output_file_name=output_file_name[:-4]
        output_file_name=output_file_name[:100]+output_extension
    ffmpeg_output_file = os.path.join(log_dir,'ffmpeg.output.'+output_file_name[:100]+'.'+process_dttm+'.txt')
    f2=open(ffmpeg_output_file,'wt+')
    f2.write('--------- PROCESS START | '+datetime.datetime.now().strftime('%Y-%m-%d  %H:%M:%S') +' ---------'+'\n')
    f2.write("-- Sonarr Environment Variables:"+'\n')
    f2.write(json.dumps(dict(os.environ),indent=1)+'\n')
    f2.write("-------------------------------------------"+'\n')
    f2.write("Mediainfo Command: \n"+ mediainfo_cmd+'\n')
    f2.write("-- Source File Mediainfo JSON Extract:"+'\n')
    f2.write(json.dumps(mediainfo,indent=1)+'\n')
    f2.write("-------------------------------------------"+'\n')
    full_output_file_name=os.path.join(encode_dir,output_file_name)
    command=[ffmpeg,'-hwaccel','cuda','-i', sonarr_episodefile_path,'-c:v:0','h264_nvenc'] + vf + ['-c:a', 'ac3', '-c:s', 'copy', '-y', '-map', '0:a', '-map', '0:v:0']+ subtitles_track_map+['-preset', 'slow', '-cq:v', quality, '-rc:v', 'vbr', '-qmin', '0', '-b:v', '0', '-max_muxing_queue_size', '1024',  full_output_file_name]
    f2.write('-- Source File:   '+sonarr_episodefile_path+'\n')
    f2.write('-- Detected Video File Attributes: '+'\n')
    f2.write("---- Interlacing: "+str(interlaced)+'\n')
    f2.write("---- Ten Bit Video: "+str(ten_bit)+'\n')
    f2.write("---- Use New File override: "+str(use_new_override)+'\n')
    f2.write("---- Move File Flag: "+str(move_files)+'\n')
    f2.write("---- New File Extension Calculated: "+output_extension+'\n')
    f2.write("-------------------------------------------"+'\n')
    f2.write("-- Input File: "+sonarr_episodefile_path+'\n')
    f2.write("-- Output File: "+full_output_file_name+'\n')
    f2.write("-------------------------------------------"+'\n')
    f2.write("-- FFMPEG Command: "+'\n')
    f2.write('---- '+' '.join(command)+'\n')
    f2.write("-------------------------------------------"+'\n')
    f2.close()
    f2=open(ffmpeg_output_file,'at+')
    time.sleep(1)
    proc = subprocess.Popen(command,shell=False, stdout=f2, stderr=f2)
    proc.wait()
    time.sleep(4)
    rc=proc.returncode
    f2.write("-------------------------------------------"+'\n')
    f2.write("ffmpeg exited with code : "+str(rc)+'\n')
    f2.write("-------------------------------------------"+'\n')
    if int(rc) != 0:
        print("oh that's bad. ffmpeg's had a problem encoding the video.")
        alert_string='ffmpeg was not able to encode the following file and will need manual intervention:\n'+sonarr_episodefile_path
        f2.write(alert_string)
        telegram_notify(telegram_user_id, telegram_bot_api_key, alert_string+'\n',f2)
        if move_files:
            os.rename(sonarr_episodefile_path,os.path.join(preproc_dir,'ffmpeg.error.'+process_dttm+'.'+sonarr_file_basename[:-4][:100]+output_extension))
        f2.close()
        exit(99)
    # -------------- check for errors -----------------
    new_size = os.path.getsize(full_output_file_name)
    orig_file_sz=os.path.getsize(sonarr_episodefile_path)
    f2.write('-- File Size Compare:'+'\n')
    f2.write("    Original File Size: "+ str(orig_file_sz)+'\n')
    f2.write("    Encoded File Size:  "+ str(new_size)+'\n')
    if new_size >= orig_file_sz and not use_new_override:
        selected_file=sonarr_episodefile_path
        f2.write("        Original file is smaller and the use new file override flag is not set"+'\n')
        f2.write(" -- Selected file for import: "+selected_file+'\n')
        if move_files:
            preproc_file=os.path.join(preproc_dir,'ffmpeg.not-smaller.'+process_dttm+'.'+sonarr_file_basename[:-4][:100]+orig_file_extension)
            os.rename(full_output_file_name,preproc_file)
            f2.write(' Moving encoded file to Preprocess Directory:'+'\n')
            f2.write('   '+full_output_file_name +' --> '+preproc_file+'\n')
            f2.write("-------------------------------------------"+'\n')
    else:
        selected_file=full_output_file_name
        f2.write("        New file is smaller"+'\n')
        f2.write(" -- Selected file for import: "+selected_file+'\n')
        if move_files:
            preproc_file=os.path.join(preproc_dir,'ffmpeg.sonarr-original.'+process_dttm+'.'+sonarr_file_basename[:-4][:100]+orig_file_extension)
            os.rename(sonarr_episodefile_path,preproc_file)
            f2.write(' Moving original file to Preprocess Directory:'+'\n')
            f2.write('   '+sonarr_episodefile_path +' --> '+preproc_file+'\n')
            f2.write("-------------------------------------------"+'\n')
    if move_files:
        sonarr_target_basename=os.path.basename(selected_file)
        sonarr_target_dir=os.path.dirname(sonarr_episodefile_path)
        sonarr_target=os.path.join(sonarr_target_dir,sonarr_target_basename)
        f2.write("Moving selected file to Sonarr's directory structure, then moving it to Plex."+'\n')
        f2.write(selected_file+' --> '+sonarr_target+'\n')
        os.rename(selected_file,sonarr_target)
        time.sleep(2)
        plex_file_path, plex_file_name=move_sonarr_to_plex(sonarr_target, sonarr_dir, plex_dir, f2, name_overrides)
        video_file_name=os.path.basename(plex_file_name)
        unmonitor_flag=unmonitor_episode(sonarr_episode_id, f2, sonarr_api_key, sonarr_host)
        if not unmonitor_flag:
            alert_string='Unable to unmonitor the episode:\n'+sonarr_episodefile_path+'\n'+'Episode ID: '+str(sonarr_episode_id)
            f2.write("-------------------------------------------"+'\n')
            f2.write(alert_string+'\n')
            telegram_notify(telegram_user_id, telegram_bot_api_key, alert_string, f2)
            #this scenario is not fatal - but it is strange and i would like to know about it.
        if not subtitles_found:
            season_num=os.environ.get('sonarr_episodefile_seasonnumber')
            episode_num=os.environ.get('sonarr_episodefile_episodenumbers')
            show_imdb_id=os.environ.get('sonarr_series_imdbid')
            subtitle_search_status=opensubtitles_api_call(ost_user_id, ost_passwd, ost_api_key,season_num, episode_num, show_imdb_id, plex_file_path, video_file_name, f2)
            if subtitle_search_status is None:
                f2.write("No eligible subtitles were found on opensubtitles.org"+'\n')
            elif not subtitle_search_status:
                f2.write("Subtitles were not downloaded successfully."+'\n')
            else:
                f2.write("Subtitles were found and downloaded."+'\n')
        plexscan_cmd=['/tools/scripts/plex_media_scanner.py','--LibraryID','2']
        plex_media_scanner=subprocess.Popen(plexscan_cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
        plex_media_output=stdout_stderr_tuple_to_string(plex_media_scanner)
        f2.write(plex_media_output+'\n')
        jfin = requests.post("https://flamedramon.micolithe.us/jellyfin/Library/Refresh", headers={'Authorization': 'MediaBrowser Token="476b35177b96439fa9d75dda9a4825cb"'}, data={})
        f2.write("** Jellyfin library scan - POST | "+jfin.url +'\n' )
        f2.write("Response Code: "+str(jfin.status_code) +'\n')

    else:
        f2.write("Move Files flag is false - Not moving original file"+'\n')
        f2.write("The output file will be moved to the dev location /data/TV_Dev_Target/"+'\n')
        os.rename(full_output_file_name,os.path.join('/data/TV_Dev_Target/',output_file_name))
    f2.close()


if __name__=='__main__':
    main()
