#!/tools/conda/envs/Plex/bin/python

import os
import subprocess
import sys
import datetime
import json
import requests


def write_log(logfile, message):
    f=open(logfile,'at')
    f.write(message+'\n')
    f.close()
    #print(message)

if __name__=="__main__":
    tg_chat_id='67388505'
    tg_api_key='5971380014:AAHHgOVmMhuMwZ6b92DYmbyCsY4JR2dfZCE'
    log_dir='/data/logs/'
    log_nm=datetime.datetime.now().strftime("%Y%m%d_%H%M%S")+'_docker_sucks_shit.txt'
    logfile_name=os.path.join(log_dir,log_nm)
    print(logfile_name)
    docker_containers=[
        {"name":"flamedramon-jellyfin" ,
         "compose_file":"/home/kronish/docker-compose-files/jellyfin/docker-compose.yml"},
        {"name":"flamedramon-pinchflat" ,
         "compose_file":"/home/kronish/docker-compose-files/pinchflat/docker-compose.yml"},
        {"name":"flamedramon-slskd2" ,
         "compose_file":"/home/kronish/docker-compose-files/slskd/docker-compose.yml"},
        {"name":"flamedramon-vaultwarden" ,
         "compose_file":"/home/kronish/docker-compose-files/vaultwarden/docker-compose.yml"},
        {"name":"flamedramon-ersatztv2" ,
         "compose_file":"/home/kronish/docker-compose-files/ersatztv/docker-compose.yml"},
        {"name":"flamedramon-adchpp" ,
         "compose_file":"/home/kronish/docker-compose-files/dcpp-adch/docker-compose.yml"},
       # {"name":"flamedramon-mssqldev" ,
       #  "compose_file":"/home/kronish/docker-compose-files/sqlserver/docker-compose.yml"},
        {"name":"flamedramon-navidrome" ,
         "compose_file":"/home/kronish/docker-compose-files/navidrome/docker-compose.yml"},
        {"name":"flamedramon-xteve2" ,
         "compose_file":"/home/kronish/docker-compose-files/xteve/docker-compose.yml"},
    ]
    notification_text=[]
    notify=False
    for dc in docker_containers:
        write_log(logfile_name, '***********************************************************\n\n')
        check_running_cmd=['docker','container','inspect','-f',"{{.State.Status}}", dc['name']]
        write_log(logfile_name, ' '.join(check_running_cmd))
        running_sproc=subprocess.Popen(check_running_cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        running_sproc_c=running_sproc.communicate()
        out,err=running_sproc_c
        status=out.decode('utf-8').strip()
        status_err=err.decode('utf-8').strip()
        write_log(logfile_name, '  '+status)
        write_log(logfile_name, '  '+status_err)
        #print(status)
        if status=='running':
            write_log(logfile_name,"Container Running: "+dc["name"])
        else:
            notify=True
            write_log(logfile_name, "Container was NOT runnning!!!! "+dc['name'])
            notification_text.append("Container was not running: "+dc['name'] +' Attempting to start it.')
            start_cmd=['docker','compose','--file',dc['compose_file'],'up','-d']
            write_log(logfile_name, ' '.join(start_cmd))
            start_sproc=subprocess.Popen(start_cmd, shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            start_sproc_c=start_sproc.communicate()
            start_out,start_err=start_sproc_c
            start_status=start_out.decode('utf-8').strip()
            start_status_err=start_err.decode('utf-8').strip()
            write_log(logfile_name, '  '+start_status)
            write_log(logfile_name, '  '+start_status_err)
            if 'Error response' in start_status or 'Error response' in start_status_err:
                notification_text.append("Failed to start the container - you might wanna check on this manually.")
            notification_text.append('')
            notification_text.append("Log File: "+logfile_name)
    if notify:
        payload_body={"chat_id":tg_chat_id,
                      "text": datetime.datetime.now().strftime('%Y-%m-%d  %H:%M:%S') + "\n\n"+  '\n'.join(notification_text)}
        url='https://api.telegram.org/bot'+tg_api_key+'/sendMessage'
        p=requests.post(url,json=payload_body)